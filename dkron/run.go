package dkron

import (
	"context"
	"fmt"
	"sync"

	"github.com/hashicorp/serf/serf"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

// Run call the agents to run a job. Returns a job with its new status and next schedule.
func (a *Agent) Run(ctx context.Context, jobName string, ex *Execution) (*Job, error) {
	ctx, span := a.tracer.Start(ctx, "agent.Run", trace.WithAttributes(attribute.String("job_name", jobName)))
	defer span.End()

	job, err := a.Store.GetJob(ctx, jobName, nil)
	if err != nil {
		return nil, fmt.Errorf("agent: Run error retrieving job: %s from store: %w", jobName, err)
	}

	// In case the job is not a child job, compute the next execution time
	if job.ParentJob == "" {
		if ej, ok := a.sched.GetEntryJob(jobName); ok {
			job.Next = ej.entry.Next
			if err := a.applySetJob(job.ToProto()); err != nil {
				return nil, fmt.Errorf("agent: Run error storing job %s before running: %w", jobName, err)
			}
		} else {
			return nil, fmt.Errorf("agent: Run error retrieving job: %s from scheduler", jobName)
		}
	}

	// In the first execution attempt we build and filter the target nodes
	// but we use the existing node target in case of retry.
	var targetNodes []Node
	if ex.Attempt <= 1 {
		targetNodes = a.getTargetNodes(job.Tags, defaultSelector)
	} else {
		for _, m := range a.serf.Members() {
			if ex.NodeName == m.Name {
				if m.Status == serf.StatusAlive {
					targetNodes = []Node{m}
					break
				}
				return nil, fmt.Errorf("retry target node is gone: %s for job %s", ex.NodeName, ex.JobName)
			}
		}
		if len(targetNodes) == 0 {
			return nil, fmt.Errorf("retry target node not found: %s for job %s", ex.NodeName, ex.JobName)
		}
	}

	// In case no nodes found, return reporting the error
	if len(targetNodes) < 1 {
		return nil, fmt.Errorf("no target nodes found to run job %s", ex.JobName)
	}
	a.logger.WithField("nodes", targetNodes).Debug("agent: Filtered nodes to run")

	var wg sync.WaitGroup
	for _, v := range targetNodes {
		// Determine node address
		addr := rpcAddrForNode(v)

		// Call here client GRPC AgentRun
		wg.Add(1)
		go func(node string, wg *sync.WaitGroup) {
			defer wg.Done()
			a.logger.WithFields(map[string]interface{}{
				"job_name": job.Name,
				"node":     node,
			}).Info("agent: Calling AgentRun")

			err := a.GRPCClient.AgentRun(node, job.ToProto(), ex.ToProto())
			if err != nil {
				a.logger.WithFields(map[string]interface{}{
					"job_name": job.Name,
					"node":     node,
				}).Error("agent: Error calling AgentRun")
			}
		}(addr, &wg)
	}

	wg.Wait()
	return job, nil
}

func (a *Agent) getRetryTargetNode(tags map[string]string, failedAgent string) (Node, bool) {
	bareTags, _ := cleanTags(tags, a.logger)
	nodes := a.getQualifyingNodes(a.serf.Members(), bareTags)
	nodes = filterArray(nodes, func(node Node) bool {
		return node.Status == serf.StatusAlive && node.Name != failedAgent
	})
	if len(nodes) == 0 {
		return Node{}, false
	}
	return nodes[defaultSelector(nodes)], true
}

func rpcAddrForNode(node Node) string {
	if addr, ok := node.Tags["rpc_addr"]; ok {
		return addr
	}
	return node.Addr.String()
}
