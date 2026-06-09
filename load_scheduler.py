import subprocess
import json
import os
import urllib.request
import urllib.error

DKRON_API_URL = os.getenv("DKRON_API_URL", "http://localhost:8080/v1").rstrip("/")
JOB_NAME = os.getenv("DKRON_JOB_NAME", "load-aware-job")

DEFAULT_AGENTS = [
    "dkron-dkron-agent-1",
    "dkron-dkron-agent-2",
    "dkron-dkron-agent-3",
    "dkron1",
    "dkron2",
    "dkron3",
]

def docker_output(*args):
    return subprocess.check_output(
        ["docker", *args],
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()

def discover_agents():
    output = docker_output("ps", "--format", "{{.Names}}")
    containers = [line.strip() for line in output.splitlines() if line.strip()]

    agent_containers = [
        name for name in containers
        if "dkron" in name.lower() and "agent" in name.lower()
    ]

    if agent_containers:
        return agent_containers

    dkron_containers = [
        name for name in containers
        if "dkron" in name.lower()
    ]

    if dkron_containers:
        return dkron_containers

    return DEFAULT_AGENTS

def get_container_stats(container_name):
    output = docker_output(
        "stats",
        container_name,
        "--no-stream",
        "--format",
        "{{.CPUPerc}} {{.MemPerc}}",
    )

    cpu_text, ram_text = output.split()

    cpu = float(cpu_text.replace("%", ""))
    ram = float(ram_text.replace("%", ""))

    return cpu, ram

def calculate_score(cpu, ram):
    return cpu + ram

def create_dkron_job(agent):
    job_tags = get_job_tags_for_agent(agent)
    job = {
        "name": JOB_NAME,
        "displayname": f"Load aware job on {agent}",
        "schedule": "@every 1h",
        "timezone": "Asia/Ho_Chi_Minh",
        "owner": "Load Aware Scheduler",
        "owner_email": "scheduler@example.com",
        "disabled": False,
        "concurrency": "allow",
        "executor": "shell",
        "executor_config": {
            "command": f"echo Hello from Load Aware Scheduler on {agent}"
        },
        "tags": job_tags,
        "metadata": {
            "selected_agent": agent,
            "load_aware": "true"
        }
    }

    print("Payload tao job Dkron:")
    print(json.dumps(job, indent=2, ensure_ascii=False))
    return post_json(f"{DKRON_API_URL}/jobs", job)

def run_dkron_job():
    try:
        return post_json(f"{DKRON_API_URL}/jobs/{JOB_NAME}/run")
    except RuntimeError as error:
        print(error)
        print("Thu endpoint run khac cua Dkron...")
        return post_json(f"{DKRON_API_URL}/jobs/{JOB_NAME}")

def post_json(url, data=None):
    body = None
    headers = {}

    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Dkron API loi {error.code} khi goi {url}:\n{error_body}"
        ) from error

def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Dkron API loi {error.code} khi goi {url}:\n{error_body}"
        ) from error

def get_job_tags_for_agent(agent):
    try:
        members = get_json(f"{DKRON_API_URL}/members")
    except Exception as error:
        print("Khong doc duoc Dkron members, target truc tiep bang tag agent.")
        print(error)
        return {"agent": f"{agent}:1"}

    print("Dkron members:")
    for member in members:
        name = member.get("Name", "")
        tags = member.get("Tags", {})
        print(f"- {name}: {tags}")

    selected_member = next(
        (member for member in members if member.get("Name") == agent),
        None,
    )

    if selected_member:
        tags = selected_member.get("Tags", {})
        if tags.get("agent"):
            print(f"Tag dung de target node {agent}: agent={tags['agent']}:1")
            return {"agent": f"{tags['agent']}:1"}

        unique_tag = find_unique_target_tag(tags, members)
        if unique_tag:
            key, value = unique_tag
            print(f"Tag dung de target node {agent}: {key}={value}:1")
            return {key: f"{value}:1"}

    print("Chua tim thay member tren Dkron API, target truc tiep bang tag agent.")
    return {"agent": f"{agent}:1"}

def find_unique_target_tag(tags, members):
    ignored_tags = {"rpc_addr", "port", "version", "server"}

    for key, value in tags.items():
        if key in ignored_tags:
            continue

        same_value_count = sum(
            1 for member in members
            if member.get("Tags", {}).get(key) == value
        )

        if same_value_count == 1:
            return key, value

    return None

best_agent = None
best_score = 999999

print("===== LOAD-AWARE SCHEDULING =====")
print(f"Dkron API: {DKRON_API_URL}")

try:
    agents = discover_agents()
except subprocess.CalledProcessError as error:
    print("Khong tu dong doc duoc danh sach Docker container.")
    print(error.output)
    agents = DEFAULT_AGENTS

print("Agents se kiem tra:")
for agent in agents:
    print(f"- {agent}")

print("---------------------------------")

for agent in agents:
    try:
        cpu, ram = get_container_stats(agent)
    except subprocess.CalledProcessError as error:
        print(f"Khong lay duoc Docker Stats cho {agent}:")
        print(error.output)
        continue

    score = calculate_score(cpu, ram)

    print(f"{agent}: CPU={cpu}% RAM={ram}% SCORE={score}")

    if score < best_score:
        best_score = score
        best_agent = agent

print("---------------------------------")
print(f"Agent duoc chon de chay job: {best_agent}")
print(f"Diem tai thap nhat: {best_score}")

if best_agent is None:
    raise RuntimeError("Khong tim thay agent hop le de chay job.")

print("---------------------------------")
print("Dang tao job tren Dkron Dashboard...")
create_response = create_dkron_job(best_agent)
print(create_response)

print("Dang run job tren Dkron...")
run_response = run_dkron_job()
print(run_response)

print("---------------------------------")
print("Hoan tat demo load-aware scheduling.")
print("Mo dashboard Dkron: http://localhost:8080")
