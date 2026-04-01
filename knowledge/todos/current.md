# Current Sprint

## Status: Agent Core Built — Awaiting VM Testing

### Completed
- [x] Project skeleton with clean separation (code in src/, context in knowledge/)
- [x] Agent config system (identity, research, interaction, schedule settings)
- [x] Session management (userId → sessionId persistence)
- [x] Two-layer prompt system (base DNA + user config layer)
- [x] Claude CLI spawner with Notion marker parsing
- [x] CLI test harness (scripts/test-agent.ts)
- [x] VM setup script (scripts/setup-vm.sh)

### In Progress
- [ ] Push to VM, run setup, authenticate Claude Code
- [ ] Test agent via CLI harness — validate research quality and prompt behavior

### Up Next
- [ ] Iterate on prompt based on test results
- [ ] WhatsApp Cloud API integration (webhook + sender)
- [ ] Notion integration (client, sync, schema)
- [ ] Watchout Protocol scheduler
- [ ] Context management (user profiles, metadata)
