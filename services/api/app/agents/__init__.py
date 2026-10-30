"""ufme agent harness: LangChain Deep Agents on any configured LLM, transparent and human-approved.

- registry: which models exist, which agent uses which, budgets and data policy
- tools: read-only ufme tools the agents may call (agents never change data)
- harness: runs an agent and turns its graph events into a live, replayable stream
- assist: ufme Assist (the Q&A panel) as a harness agent
"""
