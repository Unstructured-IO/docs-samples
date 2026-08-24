import json
import mimetypes
import os
import time

from unstructured_client import UnstructuredClient
from unstructured_client.models.operations import CreateJobRequest, DownloadJobOutputRequest
from unstructured_client.models.shared import BodyCreateJob, InputFiles

# ----------------------------------------------------------------------------------
# SET THE VARIABLES BELOW as they apply to you.
# ----------------------------------------------------------------------------------
# API_KEY is included here as a local variable for ease of use in this quickstart.
# This isn't best practice outside of local testing on your own machine. Once
# you've added your real key, don't share this file or check it into any
# repositories.
API_KEY = "YOUR_API_KEY_HERE"
# The local directory containing the file (or files) you want to process.
# This folder should contain only the file(s) you want to process, since the
# script processes every file it finds here.
INPUT_DIR = "/full/path/to/your/input/directory"
# The local directory where you want the results saved.
# Use a different folder than INPUT_DIR, or on a second run the script will
# also try to process the JSON files already saved here.
OUTPUT_DIR = "/full/path/to/your/output/directory"
# ----------------------------------------------------------------------------------

# Validate the variable settings
def validate_inputs(api_key, input_dir, output_dir):
    if api_key in ("YOUR_API_KEY_HERE", ""):
        raise SystemExit("Set API_KEY to your Unstructured API key before running this script.")
    if input_dir in ("/full/path/to/your/input/directory", ""):
        raise SystemExit("Set INPUT_DIR to the local directory containing the file (or files) you want to process before running this script.")
    if output_dir in ("/full/path/to/your/output/directory", ""):
        raise SystemExit("Set OUTPUT_DIR to the local directory where you want the results saved before running this script.")

# API_URL is already preset for you.  Do not change the value.
API_URL = "https://platform-api.transform.unstructured.io/api/v1"

validate_inputs(API_KEY, INPUT_DIR, OUTPUT_DIR)

client = UnstructuredClient(
    api_key_auth=API_KEY,
    server_url=API_URL
)

# Step 1: Create the job.
input_files = []
for filename in os.listdir(INPUT_DIR):
    full_path = os.path.join(INPUT_DIR, filename)
    if not os.path.isfile(full_path):
        continue
    content_type, _ = mimetypes.guess_type(full_path)
    input_files.append(
        InputFiles(
            content=open(full_path, "rb"),
            file_name=filename,
            content_type=content_type or "application/octet-stream"
        )
    )

try:
    response = client.jobs.create_job(
        request=CreateJobRequest(
            body_create_job=BodyCreateJob(
                request_data=json.dumps({
                    "job_nodes": [
                        {
                            "name": "Partitioner",
                            "type": "partition",
                            "subtype": "vlm",
                            "settings": {
                                "is_dynamic": True,
                                "allow_fast": True
                            }
                        }
                    ]
                }),
                input_files=input_files
            )
        )
    )
finally:
    for input_file in input_files:
        input_file.content.close()

job_id = response.job_information.id
print(f"Job ID: {job_id}")

# Step 2: Poll until the job completes.
while True:
    response = client.jobs.get_job(request={"job_id": job_id})
    job_info = response.job_information
    status = job_info.status

    print(f"Job status: {status.value}")

    if status == "COMPLETED":
        print("Job completed.")
        break
    elif status in ("FAILED", "STOPPED"):
        raise RuntimeError(f"Job did not complete successfully: {status}")

    time.sleep(10)

output_node_file_ids = [f.file_id for f in (job_info.output_node_files or [])]

# Step 3: Download the job output.
os.makedirs(OUTPUT_DIR, exist_ok=True)

for file_id in output_node_file_ids:
    response = client.jobs.download_job_output(
        request=DownloadJobOutputRequest(job_id=job_id, file_id=file_id)
    )
    output_path = os.path.join(OUTPUT_DIR, f"{file_id}.json")
    with open(output_path, "w") as f:
        json.dump(response.any, f, indent=4)
    print(f"Saved: {output_path}")
