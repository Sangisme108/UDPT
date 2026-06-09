import json
import os
import time
import urllib.error
import urllib.request

DKRON_API_URL = os.getenv("DKRON_API_URL", "http://localhost:8080/v1").rstrip("/")
JOB_NAME = os.getenv("DKRON_RETRY_JOB_NAME", "retry-reassign-demo")
MAX_RETRY = int(os.getenv("MAX_RETRY", "2"))
INITIAL_AGENT = os.getenv("INITIAL_AGENT", "dkron1")


def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Dkron API error {error.code} when calling {url}:\n{error_body}"
        ) from error


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
            f"Dkron API error {error.code} when calling {url}:\n{error_body}"
        ) from error


def discover_agents():
    members = get_json(f"{DKRON_API_URL}/members")
    agents = []

    for member in members:
        name = member.get("Name")
        tags = member.get("Tags", {})
        agent_tag = tags.get("agent")

        if agent_tag:
            agents.append(agent_tag)
        elif name:
            agents.append(name)

    return sorted(set(agents))


def choose_initial_agent(agents):
    if INITIAL_AGENT in agents:
        return INITIAL_AGENT
    return agents[0]


def choose_reassignment_agent(agents, failed_agent):
    for agent in agents:
        if agent != failed_agent:
            return agent
    raise RuntimeError("Need at least two Dkron agents to demo reassignment.")


def build_job(agent, command, retry_count):
    return {
        "name": JOB_NAME,
        "displayname": f"Retry reassignment demo on {agent}",
        "schedule": "@every 1h",
        "timezone": "Asia/Ho_Chi_Minh",
        "owner": "Retry Reassignment Demo",
        "owner_email": "scheduler@example.com",
        "disabled": False,
        "concurrency": "allow",
        "executor": "shell",
        "executor_config": {
            "command": command,
        },
        "tags": {
            "agent": f"{agent}:1",
        },
        "metadata": {
            "selected_agent": agent,
            "retry_count": str(retry_count),
            "retry_reassignment": "true",
        },
    }


def save_job(agent, command, retry_count):
    job = build_job(agent, command, retry_count)
    print("Payload:")
    print(json.dumps(job, indent=2, ensure_ascii=False))
    return post_json(f"{DKRON_API_URL}/jobs", job)


def run_job():
    return post_json(f"{DKRON_API_URL}/jobs/{JOB_NAME}/run")


def main():
    print("===== RETRY + REASSIGNMENT DEMO =====")
    print(f"Dkron API: {DKRON_API_URL}")

    agents = discover_agents()
    if not agents:
        raise RuntimeError("No Dkron agents found from /members.")

    print("Agents:")
    for agent in agents:
        print(f"- {agent}")

    initial_agent = choose_initial_agent(agents)
    retry_count = 0

    print("")
    print(f"Step 1: Create job on {initial_agent}")
    print(f"Selected initial agent: {initial_agent}")
    fail_command = 'echo "Job failed intentionally" && exit 1'
    print("Command: exit 1")
    create_response = save_job(initial_agent, fail_command, retry_count)
    print(create_response)

    print("")
    print("Step 2: Run job")
    run_response = run_job()
    print(run_response)

    # Dkron's run API returns the job object immediately. For this external demo
    # controller, the first run is intentionally treated as failed.
    time.sleep(2)
    failed_agent = initial_agent
    print(f"Job failed on agent: {failed_agent}")

    print("")
    print("Step 3: Retry check")
    retry_count += 1
    print(f"retry_count = {retry_count}")
    print(f"max_retry = {MAX_RETRY}")

    if retry_count > MAX_RETRY:
        print("Retry limit exceeded. Stop reassignment.")
        print("===== DEMO FINISHED =====")
        return

    new_agent = choose_reassignment_agent(agents, failed_agent)

    print("")
    print("Step 4: Reassign job")
    print(f"Failed agent: {failed_agent}")
    print(f"New agent: {new_agent}")
    success_command = 'echo "Retry success on reassigned agent" && exit 0'
    update_response = save_job(new_agent, success_command, retry_count)
    print(update_response)

    print("")
    print("Step 5: Run retry job")
    retry_response = run_job()
    print(retry_response)
    time.sleep(2)
    print(f"Retry success on reassigned agent: {new_agent}")

    print("===== DEMO FINISHED =====")
    print("Open Dkron dashboard: http://localhost:8080")


if __name__ == "__main__":
    main()
