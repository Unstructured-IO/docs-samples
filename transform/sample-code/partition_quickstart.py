import json
import mimetypes
import os
import time

from unstructured_client import UnstructuredClient
from unstructured_client.models.operations import CreateJobRequest, DownloadJobOutputRequest
from unstructured_client.models.shared import BodyCreateJob, InputFiles

# API_KEY is included here as a local variable for ease of use in this quickstart.
# This isn't best practice outside of local testing on your own machine. Once
# you've added your real key, don't share this file or check it into any
# repositories.
API_KEY = ""
API_URL = "https://platform-api.transform.unstructured.io"
# The local directory containing the file (or files) you want to process.
INPUT_DIR = "/full/path/to/your/input/directory"
# The local directory where you want the results saved.
OUTPUT_DIR = "/full/path/to/your/output/directory"

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
