"""
CloudWatch Metrics Toolkit for Incident Commander

Queries real CloudWatch Metrics instead of mock JSON data.
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, List
import statistics

cloudwatch = boto3.client("cloudwatch")

FUNCTION_NAME = "demo-checkout-service"


def query_metrics(service: str, metric: str, time_window_minutes: int) -> Dict:
    """
    Query CloudWatch Metrics for performance data

    Args:
        service: Service name (Lambda function)
        metric: Metric to query (p99_latency_ms, error_rate, etc.)
        time_window_minutes: How far back to query

    Returns:
        Dict with current value, percentiles, spike detection
    """

    # Map generic metric names to Lambda metrics
    metric_mapping = {
        "p99_latency_ms": "Duration",
        "error_rate": "Errors",
        "error_count": "Errors",
        "concurrency": "ConcurrentExecutions",
        "throttles": "Throttles",
        "invocations": "Invocations",
    }

    cloudwatch_metric = metric_mapping.get(metric, metric)

    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=time_window_minutes)

    print(f"📊 Querying CloudWatch Metrics for {service}")
    print(f"   Metric: {cloudwatch_metric}")
    print(f"   Time window: {time_window_minutes} minutes")

    try:
        # Get metric statistics
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName=cloudwatch_metric,
            Dimensions=[{"Name": "FunctionName", "Value": FUNCTION_NAME}],
            StartTime=start_time,
            EndTime=end_time,
            Period=60,  # 1-minute granularity
            Statistics=["Average", "Maximum", "Minimum", "SampleCount"],
            ExtendedStatistics=["p99"] if cloudwatch_metric == "Duration" else [],
        )

        datapoints = sorted(response["Datapoints"], key=lambda x: x["Timestamp"])

        if not datapoints:
            print(f"   ⚠️  No data available for {cloudwatch_metric}")
            return {
                "error": "No data available",
                "current_value": 0,
                "spike_detected": False,
            }

        print(f"   ✅ Retrieved {len(datapoints)} data points")

        # Calculate statistics
        averages = [d["Average"] for d in datapoints]
        maximums = [d["Maximum"] for d in datapoints]
        minimums = [d["Minimum"] for d in datapoints]

        current_value = averages[-1] if averages else 0
        p50 = statistics.median(averages)
        p99 = max(maximums) if maximums else 0

        # Spike detection (simple threshold-based)
        # Baseline: average of all points except the last 10
        if len(averages) > 10:
            baseline = statistics.mean(averages[:-10])
        else:
            baseline = p50

        # Spike if current > 2x baseline
        spike_detected = current_value > baseline * 2
        spike_start_time = None

        if spike_detected:
            # Find when spike started
            for i, dp in enumerate(datapoints):
                if dp["Average"] > baseline * 2:
                    spike_start_time = dp["Timestamp"]
                    break

        print(
            f"   Current: {current_value:.2f}, Baseline: {baseline:.2f}, p99: {p99:.2f}"
        )
        if spike_detected:
            print(f"   🚨 SPIKE DETECTED! {(current_value / baseline):.1f}x baseline")

        return {
            "metric_name": cloudwatch_metric,
            "current_value": current_value,
            "p50": p50,
            "p99": p99,
            "baseline": baseline,
            "spike_detected": spike_detected,
            "spike_start_time": spike_start_time.isoformat()
            if spike_start_time
            else None,
            "spike_magnitude": current_value / baseline if baseline > 0 else 1.0,
            "datapoints_count": len(datapoints),
            "min_value": min(minimums) if minimums else 0,
            "max_value": max(maximums) if maximums else 0,
        }

    except Exception as e:
        print(f"   ❌ Error querying metrics: {e}")
        return {"error": str(e), "current_value": 0, "spike_detected": False}


def detect_anomalies(service: str, metric: str, lookback_hours: int = 24) -> List[Dict]:
    """
    Statistical anomaly detection using CloudWatch metrics

    Args:
        service: Service name
        metric: Metric to analyze
        lookback_hours: How far back to analyze

    Returns:
        List of detected anomalies with timestamps
    """
    metric_mapping = {
        "p99_latency_ms": "Duration",
        "error_rate": "Errors",
        "concurrency": "ConcurrentExecutions",
    }

    cloudwatch_metric = metric_mapping.get(metric, metric)

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=lookback_hours)

    print(f"🔬 Running anomaly detection for {cloudwatch_metric}")
    print(f"   Lookback: {lookback_hours} hours")

    try:
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName=cloudwatch_metric,
            Dimensions=[{"Name": "FunctionName", "Value": FUNCTION_NAME}],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,  # 5-minute granularity
            Statistics=["Average", "Maximum"],
        )

        datapoints = sorted(response["Datapoints"], key=lambda x: x["Timestamp"])

        if len(datapoints) < 10:
            print(f"   ⚠️  Insufficient data for anomaly detection")
            return []

        # Simple anomaly detection: 3-sigma rule
        averages = [d["Average"] for d in datapoints]
        mean = statistics.mean(averages)
        stdev = statistics.stdev(averages)
        threshold = mean + (3 * stdev)

        anomalies = []
        for dp in datapoints:
            if dp["Average"] > threshold:
                anomalies.append(
                    {
                        "timestamp": dp["Timestamp"].isoformat(),
                        "value": dp["Average"],
                        "threshold": threshold,
                        "deviation": (dp["Average"] - mean) / stdev,
                    }
                )

        print(f"   ✅ Detected {len(anomalies)} anomalies (threshold: {threshold:.2f})")

        return anomalies

    except Exception as e:
        print(f"   ❌ Error in anomaly detection: {e}")
        return []


def get_metrics_summary(time_window_minutes: int = 30) -> Dict:
    """
    Get comprehensive metrics summary for the demo service

    Args:
        time_window_minutes: Time window to analyze

    Returns:
        Dict with summary of all key metrics
    """
    print(f"📋 Generating metrics summary for {time_window_minutes}min window\n")

    summary = {
        "time_window_minutes": time_window_minutes,
        "timestamp": datetime.now().isoformat(),
    }

    # Query multiple metrics
    metrics_to_query = [
        ("p99_latency_ms", "Duration"),
        ("error_count", "Errors"),
        ("invocations", "Invocations"),
        ("throttles", "Throttles"),
    ]

    for metric_name, _ in metrics_to_query:
        result = query_metrics(FUNCTION_NAME, metric_name, time_window_minutes)
        summary[metric_name] = result
        print()  # Spacing between metrics

    return summary


# For local testing
if __name__ == "__main__":
    print("Testing CloudWatch Metrics Toolkit\n")

    # Test metric query
    result = query_metrics(
        service="demo-checkout-service", metric="p99_latency_ms", time_window_minutes=30
    )

    print(f"\nResult: {result}")

    # Test comprehensive summary
    print("\n" + "=" * 60 + "\n")
    summary = get_metrics_summary(time_window_minutes=30)

    print(f"\nSummary generated at: {summary['timestamp']}")
    print(
        f"Spikes detected: {sum(1 for k, v in summary.items() if isinstance(v, dict) and v.get('spike_detected'))}"
    )
