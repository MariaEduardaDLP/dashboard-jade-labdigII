from shared.catalog import MESSAGES
from frontend.jade.charts import usage_chart
from frontend.jade.metrics import message_counts


def test_usage_bubbles_use_area_for_counts_and_keep_message_labels(events):
    counts = message_counts(events, [message.id for message in MESSAGES])
    chart = usage_chart(counts)
    rendered = {}
    for trace in chart.data:
        assert trace.type == "scatter"
        assert trace.mode == "markers"
        assert trace.marker.sizemode == "area"
        for label, count, size in zip(trace.y, trace.x, trace.marker.size):
            assert count == size
            rendered[label] = count
    assert rendered == dict(zip(counts["message"], counts["count"]))
