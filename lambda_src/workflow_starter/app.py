from __future__ import annotations

import json
import os

import boto3

from common.image_utils import parse_s3_records_from_sqs_event

stepfunctions = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]


def handler(event, _context):
    executions = []
    for record in parse_s3_records_from_sqs_event(event):
        response = stepfunctions.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(record),
        )
        executions.append(
            {
                "imageId": record["imageId"],
                "executionArn": response["executionArn"],
            }
        )

    return {
        "started": len(executions),
        "executions": executions,
    }

