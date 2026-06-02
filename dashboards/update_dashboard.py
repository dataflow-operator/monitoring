#!/usr/bin/env python3
"""Transform grafana-dashboard.json per improvement plan. Run from repo root."""
import copy
import json
import re
import sys
from pathlib import Path

DASHBOARD_PATH = Path(__file__).parent / "grafana-dashboard.json"
HELM_DASHBOARD_PATH = (
    Path(__file__).parent.parent.parent
    / "helm-charts/charts/dataflow-operator/dashboards/grafana-dashboard.json"
)

NS_FILTER = 'namespace=~"$namespace", name=~"$dataflow"'
PROM_DS = {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}


def prom_target(expr, legend="__auto", ref_id="A", instant=False):
    t = {
        "datasource": copy.deepcopy(PROM_DS),
        "expr": expr,
        "legendFormat": legend,
        "refId": ref_id,
    }
    if instant:
        t["format"] = "table"
        t["instant"] = True
    return t


def stat_panel(panel_id, title, expr, grid, unit="short", thresholds=None, desc=None):
    steps = thresholds or [{"color": "green", "value": None}]
    p = {
        "datasource": copy.deepcopy(PROM_DS),
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": {"mode": "absolute", "steps": steps},
                "unit": unit,
            },
            "overrides": [],
        },
        "gridPos": dict(grid),
        "id": panel_id,
        "options": {
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        "pluginVersion": "10.0.0",
        "targets": [prom_target(expr)],
        "title": title,
        "type": "stat",
    }
    if desc:
        p["description"] = desc
    return p


def row_panel(panel_id, title, y):
    return {
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "id": panel_id,
        "panels": [],
        "title": title,
        "type": "row",
    }


def timeseries_panel(panel_id, title, targets, grid, unit="short", desc=None):
    p = {
        "datasource": copy.deepcopy(PROM_DS),
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisCenteredZero": False,
                    "axisColorMode": "text",
                    "axisLabel": "",
                    "axisPlacement": "auto",
                    "barAlignment": 0,
                    "drawStyle": "line",
                    "fillOpacity": 10,
                    "gradientMode": "none",
                    "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                    "lineInterpolation": "linear",
                    "lineWidth": 1,
                    "pointSize": 5,
                    "scaleDistribution": {"type": "linear"},
                    "showPoints": "never",
                    "spanNulls": False,
                    "stacking": {"group": "A", "mode": "none"},
                    "thresholdsStyle": {"mode": "off"},
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}],
                },
                "unit": unit,
            },
            "overrides": [],
        },
        "gridPos": dict(grid),
        "id": panel_id,
        "options": {
            "legend": {
                "calcs": ["lastNotNull", "max", "mean"],
                "displayMode": "table",
                "placement": "bottom",
            },
            "tooltip": {"mode": "multi"},
        },
        "targets": targets,
        "title": title,
        "type": "timeseries",
    }
    if desc:
        p["description"] = desc
    return p


def table_panel(panel_id, title, expr, grid, transforms, desc=None):
    p = {
        "datasource": copy.deepcopy(PROM_DS),
        "fieldConfig": {
            "defaults": {
                "custom": {"align": "auto", "cellOptions": {"type": "auto"}, "inspect": False},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}],
                },
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Value"},
                    "properties": [
                        {"id": "custom.displayMode", "value": "color-background"},
                        {
                            "id": "thresholds",
                            "value": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "red", "value": None},
                                    {"color": "green", "value": 1},
                                ],
                            },
                        },
                    ],
                }
            ],
        },
        "gridPos": dict(grid),
        "id": panel_id,
        "options": {
            "cellHeight": "sm",
            "footer": {"countRows": False, "fields": "", "reducer": ["sum"], "show": False},
            "showHeader": True,
        },
        "pluginVersion": "10.0.0",
        "targets": [prom_target(expr, instant=True)],
        "title": title,
        "transformations": transforms,
        "type": "table",
    }
    if desc:
        p["description"] = desc
    return p


def heatmap_panel(panel_id, title, expr, grid, desc=None):
    p = {
        "datasource": copy.deepcopy(PROM_DS),
        "fieldConfig": {"defaults": {"custom": {"hideFrom": {"legend": False, "tooltip": False, "viz": False}}}, "overrides": []},
        "gridPos": dict(grid),
        "id": panel_id,
        "options": {
            "calculate": False,
            "cellGap": 1,
            "color": {"exponent": 0.5, "fill": "dark-orange", "mode": "scheme", "scheme": "Oranges", "steps": 64},
            "exemplars": {"color": "rgba(255,0,255,0.7)"},
            "filterValues": {"le": 1e-9},
            "legend": {"show": True},
            "rowsFrame": {"layout": "auto"},
            "tooltip": {"show": True, "yHistogram": False},
            "yAxis": {"axisPlacement": "left", "reverse": False, "unit": "s"},
        },
        "pluginVersion": "10.0.0",
        "targets": [
            {
                "datasource": copy.deepcopy(PROM_DS),
                "expr": expr,
                "format": "heatmap",
                "legendFormat": "{{stage}}",
                "refId": "A",
            }
        ],
        "title": title,
        "type": "heatmap",
    }
    if desc:
        p["description"] = desc
    return p


def piechart_panel(panel_id, title, expr, grid):
    return {
        "datasource": copy.deepcopy(PROM_DS),
        "fieldConfig": {
            "defaults": {"color": {"mode": "palette-classic"}, "mappings": []},
            "overrides": [],
        },
        "gridPos": dict(grid),
        "id": panel_id,
        "options": {
            "legend": {"displayMode": "table", "placement": "right", "values": ["value"]},
            "pieType": "donut",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "tooltip": {"mode": "single"},
        },
        "pluginVersion": "10.0.0",
        "targets": [prom_target(expr, "{{phase}}")],
        "title": title,
        "type": "piechart",
    }


def walk_replace_interval(obj):
    if isinstance(obj, str):
        return obj.replace("[5m]", "[$interval]").replace(
            "avg(dataflow_processing_duration_seconds{",
            "HISTOGRAM_AVG_PLACEHOLDER{",
        )
    if isinstance(obj, dict):
        return {k: walk_replace_interval(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk_replace_interval(v) for v in obj]
    return obj


def fix_histogram_avg(expr: str) -> str:
    if "HISTOGRAM_AVG_PLACEHOLDER" not in expr:
        return expr
    return (
        'sum(rate(dataflow_processing_duration_seconds_sum{namespace=~"$namespace", name=~"$dataflow"}[$interval])) by (namespace, name)'
        ' / '
        'sum(rate(dataflow_processing_duration_seconds_count{namespace=~"$namespace", name=~"$dataflow"}[$interval])) by (namespace, name)'
    )


def fix_targets(panel):
    if "targets" not in panel:
        return
    for t in panel["targets"]:
        if "expr" in t:
            t["expr"] = fix_histogram_avg(t["expr"])
            if "legendFormat" in t and "avg -" in t.get("legendFormat", ""):
                t["legendFormat"] = "mean - {{namespace}}/{{name}}"


def enhance_timeseries_legend(panel):
    if panel.get("type") != "timeseries":
        return
    opts = panel.setdefault("options", {})
    leg = opts.setdefault("legend", {})
    leg["calcs"] = ["lastNotNull", "max", "mean"]
    leg["displayMode"] = "table"
    leg["placement"] = "bottom"
    opts["tooltip"] = {"mode": "multi"}


def main():
    with open(DASHBOARD_PATH) as f:
        dash = json.load(f)

    dash = walk_replace_interval(dash)

    by_id = {p["id"]: p for p in dash["panels"] if "id" in p}

    # Fix success rate: avg -> min
    if 20 in by_id:
        for t in by_id[20]["targets"]:
            if "avg(dataflow_task_success_rate" in t.get("expr", ""):
                t["expr"] = t["expr"].replace("avg(", "min(")

    # Fix panel 5 histogram avg
    if 5 in by_id:
        fix_targets(by_id[5])

    # Operator resource namespace filter
    for pid in (26, 27):
        if pid in by_id:
            for t in by_id[pid]["targets"]:
                e = t.get("expr", "")
                if "container=\"dataflow-operator\"" in e and "namespace=~" not in e:
                    t["expr"] = e.replace(
                        'container="dataflow-operator"',
                        'container="dataflow-operator", namespace=~"$namespace"',
                    )

    # Enhance key timeseries legends
    for pid in (1, 2, 3, 4, 5, 6, 21, 3, 4):
        if pid in by_id:
            enhance_timeseries_legend(by_id[pid])

    # Extract existing panels (keep modifications), rebuild layout
    existing_ids = {
        100, 13, 14, 15, 16, 17, 19, 20,
        101, 1, 2,
        102, 3, 4,
        109, 40, 41, 42, 43, 44, 45, 46,
        110, 47, 48, 49, 50,
        103, 5, 6, 21,
        111, 51, 52, 53,
        104, 22, 23, 24, 25,
        105, 18,
        106, 7, 8, 9, 10,
        107, 11, 12,
        112, 54, 55, 56,
        108, 26, 27, 28, 29, 30,
        35,
    }

    f = NS_FILTER
    error_rate_expr = (
        f"(sum(rate(dataflow_connector_errors_total{{{f}}}["
        f"$interval])) + sum(rate(dataflow_transformer_errors_total{{{f}}}[$interval]))) "
        f"/ sum(rate(dataflow_messages_received_total{{{f}}}[$interval])) * 100"
    )
    stalled_expr = (
        f'count(dataflow_status{{{f}, phase="Running"}} == 1 '
        f"and ("
        f'sum(rate(dataflow_messages_received_total{{{f}}}[$interval])) by (namespace, name) == 0 '
        f'or sum(rate(dataflow_messages_sent_total{{{f}}}[$interval])) by (namespace, name) == 0'
        f")"
        f") or vector(0)"
    )
    # Simpler stalled count for stat panel
    stalled_expr = (
        f"count("
        f'  (dataflow_status{{{f}, phase="Running"}} == 1)'
        f"  * on(namespace, name) ("
        f"    (sum(rate(dataflow_messages_received_total{{{f}}}[$interval])) by (namespace, name) == 0)"
        f"    or"
        f"    (sum(rate(dataflow_messages_sent_total{{{f}}}[$interval])) by (namespace, name) == 0)"
        f"  )"
        f") or vector(0)"
    )

    p95_proc = (
        f"histogram_quantile(0.95, sum(rate(dataflow_processing_duration_seconds_bucket{{{f}}}[$interval])) by (namespace, name, le))"
    )
    p99_e2e = (
        f"histogram_quantile(0.99, sum(rate(dataflow_task_end_to_end_latency_seconds_bucket{{{f}}}[$interval])) by (namespace, name, le))"
    )
    kafka_timeout = (
        f'sum(rate(dataflow_connector_errors_total{{{f}, operation="read", error_type="request_timed_out"}}[$interval]))'
    )

    new_panels_defs = []

    # --- Overview extras ---
    new_panels_defs.extend(
        [
            stat_panel(
                31,
                "Error rate",
                error_rate_expr,
                {"h": 4, "w": 4, "x": 8, "y": 0},
                unit="percent",
                thresholds=[
                    {"color": "green", "value": None},
                    {"color": "yellow", "value": 0.5},
                    {"color": "red", "value": 1},
                ],
                desc="(connector + transformer errors) / messages received",
            ),
            stat_panel(
                32,
                "Max queue",
                f"max(dataflow_task_queue_size{{{f}}})",
                {"h": 4, "w": 4, "x": 12, "y": 0},
                thresholds=[
                    {"color": "green", "value": None},
                    {"color": "yellow", "value": 500},
                    {"color": "red", "value": 1000},
                ],
            ),
            stat_panel(
                33,
                "Active messages",
                f"sum(dataflow_task_active_messages{{{f}}})",
                {"h": 4, "w": 4, "x": 16, "y": 0},
            ),
            stat_panel(
                34,
                "Stalled pipelines",
                stalled_expr,
                {"h": 4, "w": 4, "x": 20, "y": 0},
                thresholds=[
                    {"color": "green", "value": None},
                    {"color": "red", "value": 1},
                ],
                desc="Running DataFlows with zero message throughput",
            ),
            piechart_panel(
                35,
                "DataFlow phases",
                f"count(dataflow_status{{{f}}}) by (phase)",
                {"h": 6, "w": 24, "x": 0, "y": 0},
            ),
        ]
    )

    # --- SLO row ---
    slo_stats = [
        (
            40,
            "SLO: Error rate",
            error_rate_expr,
            "percent",
            [
                {"color": "green", "value": None},
                {"color": "yellow", "value": 0.5},
                {"color": "red", "value": 1},
            ],
            "Alert: DataFlowHighErrorRate (>1%)",
        ),
        (
            41,
            "SLO: p95 processing",
            p95_proc,
            "s",
            [
                {"color": "green", "value": None},
                {"color": "red", "value": 1},
            ],
            "Alert: DataFlowSlowProcessing (>1s)",
        ),
        (
            42,
            "SLO: Task success",
            f"min(dataflow_task_success_rate{{{f}}}) * 100",
            "percent",
            [
                {"color": "red", "value": None},
                {"color": "yellow", "value": 95},
                {"color": "green", "value": 99},
            ],
            "Alert: DataFlowLowTaskSuccessRate (<95%)",
        ),
        (
            43,
            "SLO: Max queue",
            f"max(dataflow_task_queue_size{{{f}}})",
            "short",
            [
                {"color": "green", "value": None},
                {"color": "red", "value": 1000},
            ],
            "Alert: DataFlowHighQueueSize (>1000)",
        ),
        (
            44,
            "SLO: p99 E2E",
            p99_e2e,
            "s",
            [
                {"color": "green", "value": None},
                {"color": "red", "value": 5},
            ],
            "Alert: DataFlowHighE2ELatency (>5s)",
        ),
        (
            45,
            "SLO: Kafka timeouts/s",
            kafka_timeout,
            "ops",
            [
                {"color": "green", "value": None},
                {"color": "red", "value": 0.1},
            ],
            "Alert: DataFlowKafkaFetchTimeouts (>0.1/s)",
        ),
        (
            46,
            "SLO: Disconnected",
            f"count(dataflow_connector_connection_status{{{f}}} == 0) or vector(0)",
            "short",
            [
                {"color": "green", "value": None},
                {"color": "red", "value": 1},
            ],
            "Alert: DataFlowConnectorDisconnected",
        ),
    ]
    for i, (pid, title, expr, unit, thr, desc) in enumerate(slo_stats):
        new_panels_defs.append(
            stat_panel(pid, title, expr, {"h": 4, "w": 3, "x": i * 3, "y": 0}, unit=unit, thresholds=thr, desc=desc)
        )

    poll_transform = [
        {
            "id": "organize",
            "options": {
                "excludeByName": {"Time": True, "__name__": True},
                "renameByName": {
                    "namespace": "Namespace",
                    "name": "Name",
                    "connector_type": "Type",
                    "connector_name": "Connector",
                    "Value": "Healthy",
                },
            },
        }
    ]

    new_panels_defs.extend(
        [
            table_panel(
                47,
                "Source poll health",
                f"dataflow_connector_source_poll_healthy{{{f}}}",
                {"h": 8, "w": 12, "x": 0, "y": 0},
                poll_transform,
                desc="1 = last polling read succeeded, 0 = failure",
            ),
            timeseries_panel(
                48,
                "Active messages (gauge)",
                [prom_target(f"dataflow_task_active_messages{{{f}}}", "{{namespace}}/{{name}}")],
                {"h": 8, "w": 12, "x": 12, "y": 0},
            ),
            timeseries_panel(
                49,
                "Stage errors rate",
                [
                    prom_target(
                        f"sum(rate(dataflow_task_stage_errors_total{{{f}}}[$interval])) by (namespace, name, stage)",
                        "{{namespace}}/{{name}} - {{stage}}",
                    )
                ],
                {"h": 8, "w": 12, "x": 0, "y": 0},
            ),
            timeseries_panel(
                50,
                "Kafka fetch timeouts",
                [
                    prom_target(
                        f'sum(rate(dataflow_connector_errors_total{{{f}, operation="read", error_type="request_timed_out"}}[$interval])) by (namespace, name, connector_name)',
                        "{{namespace}}/{{name}} - {{connector_name}}",
                    )
                ],
                {"h": 8, "w": 12, "x": 12, "y": 0},
                desc="request_timed_out on connector read",
            ),
        ]
    )

    stage_duration_expr = (
        f"histogram_quantile(0.95, sum(rate(dataflow_task_stage_duration_seconds_bucket{{{f}}}[$interval])) by (namespace, name, stage, le))"
    )
    stage_latency_expr = (
        f"histogram_quantile(0.95, sum(rate(dataflow_task_stage_latency_seconds_bucket{{{f}}}[$interval])) by (namespace, name, from_stage, to_stage, le))"
    )
    heatmap_expr = (
        f"sum(rate(dataflow_task_stage_duration_seconds_bucket{{{f}}}[$interval])) by (le, stage)"
    )

    new_panels_defs.extend(
        [
            heatmap_panel(
                51,
                "Stage duration heatmap",
                heatmap_expr,
                {"h": 8, "w": 24, "x": 0, "y": 0},
                desc="Rate by stage and histogram bucket",
            ),
            timeseries_panel(
                52,
                "Stage duration p95",
                [prom_target(stage_duration_expr, "p95 - {{namespace}}/{{name}} - {{stage}}")],
                {"h": 8, "w": 12, "x": 0, "y": 0},
                unit="s",
            ),
            timeseries_panel(
                53,
                "Stage-to-stage latency p95",
                [prom_target(stage_latency_expr, "{{from_stage}} -> {{to_stage}}")],
                {"h": 8, "w": 12, "x": 12, "y": 0},
                unit="s",
            ),
        ]
    )

    new_panels_defs.extend(
        [
            stat_panel(
                54,
                "Reconcile in-flight",
                "dataflow_controller_reconcile_inflight",
                {"h": 4, "w": 6, "x": 0, "y": 0},
                desc="Operator controller (not filtered by DataFlow)",
            ),
            timeseries_panel(
                55,
                "Reconcile duration p95",
                [
                    prom_target(
                        'histogram_quantile(0.95, sum(rate(dataflow_controller_reconcile_duration_seconds_bucket[$interval])) by (result, le))',
                        "p95 - {{result}}",
                    )
                ],
                {"h": 8, "w": 9, "x": 6, "y": 0},
                unit="s",
            ),
            timeseries_panel(
                56,
                "Reconcile errors",
                [
                    prom_target(
                        "sum(rate(dataflow_controller_reconcile_errors_total[$interval])) by (stage)",
                        "{{stage}}",
                    )
                ],
                {"h": 8, "w": 9, "x": 15, "y": 0},
            ),
        ]
    )

    new_by_id = {p["id"]: p for p in new_panels_defs}

    # Layout sections: (row_id, row_title, panel_ids, heights per row of panels)
    layout = [
        (100, "Overview", [13, 14, 15, 16, 17], 4, 4),  # row1 stats w=4
        (None, None, [19, 20, 31, 32, 33, 34], 4, 4),  # row2
        (None, None, [35], 6, 24),  # pie full width
        (109, "SLO & Alerts", [40, 41, 42, 43, 44, 45, 46], 4, 3),
        (101, "Messages", [1, 2], 8, 12),
        (102, "Errors", [3, 4], 8, 12),
        (110, "Pipeline health", [47, 48, 49, 50], 8, 12),
        (103, "Latency", [5, 6], 8, 12),
        (None, None, [21], 8, 12),  # e2e full width - use w=24
        (111, "Stages", [51], 8, 24),
        (None, None, [52, 53], 8, 12),
        (104, "Queues and load", [22, 23], 8, 12),
        (None, None, [24, 25], 8, 12),
        (105, "Operations", [18], 8, 24),
        (106, "Status", [7, 8], 8, 12),
        (None, None, [9, 10], 8, 12),
        (107, "Transformers", [11, 12], 8, 12),
        (112, "Operator controller", [54, 55, 56], 8, None),  # custom widths
        (108, "Resources", [26, 27], 8, 12),
        (None, None, [28, 29], 8, 12),
        (None, None, [30], 8, 24),
    ]

    panels_out = []
    y = 0

    def add_row(rid, title):
        nonlocal y
        panels_out.append(row_panel(rid, title, y))
        y += 1

    def add_panel_row(panel_ids, h, default_w):
        nonlocal y
        n = len(panel_ids)
        if n == 0:
            return
        if default_w == 24 and n == 1:
            pid = panel_ids[0]
            p = copy.deepcopy(by_id.get(pid) or new_by_id[pid])
            p["gridPos"] = {"h": h, "w": 24, "x": 0, "y": y}
            panels_out.append(p)
            y += h
            return
        w = default_w if default_w else 24 // n
        for i, pid in enumerate(panel_ids):
            p = copy.deepcopy(by_id.get(pid) or new_by_id[pid])
            if pid == 54:
                p["gridPos"] = {"h": 4, "w": 6, "x": 0, "y": y}
            elif pid == 55:
                p["gridPos"] = {"h": 8, "w": 9, "x": 6, "y": y}
            elif pid == 56:
                p["gridPos"] = {"h": 8, "w": 9, "x": 15, "y": y}
            elif pid == 21 and n == 1:
                p["gridPos"] = {"h": h, "w": 24, "x": 0, "y": y}
            else:
                p["gridPos"] = {"h": h, "w": w, "x": i * w, "y": y}
            panels_out.append(p)
        if 54 in panel_ids:
            y += 8
        else:
            y += h

    last_row_id = None
    for item in layout:
        row_id, row_title, pids, h, w = item
        if row_id is not None:
            add_row(row_id, row_title)
            last_row_id = row_id
        add_panel_row(pids, h, w)

    dash["panels"] = panels_out
    dash["graphTooltip"] = 1
    dash["version"] = 2
    dash["description"] = (
        "DataFlow Operator monitoring: manifests, SLOs (aligned with PrometheusRule alerts), "
        "messages, pipeline health, stages, latency, queues, operator reconcile, resources. "
        "Requires Prometheus; cAdvisor/kubelet for container_* panels. "
        "Docs: docs/docs/en/metrics.md"
    )
    dash["links"].append(
        {
            "asDropdown": False,
            "icon": "external link",
            "includeVars": True,
            "keepTime": True,
            "tags": [],
            "targetBlank": True,
            "title": "Prometheus alerts",
            "tooltip": "PrometheusRule definitions",
            "type": "link",
            "url": "https://github.com/dataflow-operator/dataflow-operator/blob/main/monitoring/alerts/prometheusrule.yaml",
        }
    )

    interval_var = {
        "current": {"selected": True, "text": "5m", "value": "5m"},
        "hide": 0,
        "includeAll": False,
        "label": "Rate interval",
        "multi": False,
        "name": "interval",
        "options": [
            {"selected": True, "text": "5m", "value": "5m"},
            {"selected": False, "text": "15m", "value": "15m"},
            {"selected": False, "text": "1h", "value": "1h"},
        ],
        "query": "5m,15m,1h",
        "queryValue": "",
        "skipUrlSync": False,
        "type": "custom",
    }
    dash["templating"]["list"].insert(1, interval_var)

    with open(DASHBOARD_PATH, "w") as f:
        json.dump(dash, f, indent=2)
        f.write("\n")

    import shutil

    shutil.copy(DASHBOARD_PATH, HELM_DASHBOARD_PATH)
    print(f"Updated {DASHBOARD_PATH} and {HELM_DASHBOARD_PATH}")
    print(f"Panels: {len(panels_out)}")


if __name__ == "__main__":
    main()
