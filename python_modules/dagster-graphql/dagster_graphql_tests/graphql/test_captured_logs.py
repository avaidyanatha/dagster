from dagster_graphql.test.utils import (
    execute_dagster_graphql,
    execute_dagster_graphql_subscription,
    infer_pipeline_selector,
)

from dagster._core.events import DagsterEventType

from .graphql_context_test_suite import ExecutingGraphQLContextTestMatrix
from .utils import sync_execute_get_run_log_data

CAPTURED_LOGS_QUERY = """
  query CapturedLogsQuery($runId: ID!, $fileKey: String!) {
    pipelineRunOrError(runId: $runId) {
      ... on PipelineRun {
        runId
        capturedLogs(fileKey: $fileKey) {
          stdout
        }
      }
    }
  }
"""

CAPTURED_LOGS_SUBSCRIPTION = """
  subscription CapturedLogsSubscription($logKey: [String!]!) {
    capturedLogs(logKey: $logKey) {
      stdout
      stderr
      cursor
    }
  }
"""


class TestCapturedLogs(ExecutingGraphQLContextTestMatrix):
    def test_get_captured_logs_over_graphql(self, graphql_context, snapshot):
        selector = infer_pipeline_selector(graphql_context, "spew_pipeline")
        payload = sync_execute_get_run_log_data(
            context=graphql_context,
            variables={"executionParams": {"selector": selector, "mode": "default"}},
        )
        run_id = payload["run"]["runId"]

        logs = graphql_context.instance.all_logs(run_id, of_type=DagsterEventType.LOGS_CAPTURED)
        assert len(logs) == 1
        entry = logs[0]
        result = execute_dagster_graphql(
            graphql_context,
            CAPTURED_LOGS_QUERY,
            variables={"runId": run_id, "fileKey": entry.dagster_event.logs_captured_data.file_key},
        )
        stdout = result.data["pipelineRunOrError"]["capturedLogs"]["stdout"]
        snapshot.assert_match(stdout)

    def test_captured_logs_subscription_graphql(self, graphql_context):
        selector = infer_pipeline_selector(graphql_context, "spew_pipeline")
        payload = sync_execute_get_run_log_data(
            context=graphql_context,
            variables={"executionParams": {"selector": selector, "mode": "default"}},
        )
        run_id = payload["run"]["runId"]
        logs = graphql_context.instance.all_logs(run_id, of_type=DagsterEventType.LOGS_CAPTURED)
        assert len(logs) == 1
        entry = logs[0]
        log_key = [run_id, "compute_logs", entry.dagster_event.logs_captured_data.file_key]

        results = execute_dagster_graphql_subscription(
            graphql_context,
            CAPTURED_LOGS_SUBSCRIPTION,
            variables={"logKey": log_key},
        )

        assert len(results) == 1
        stdout = results[0].data["capturedLogs"]["stdout"]
        assert stdout == "HELLO WORLD\n"
