# Ansible / Jetstream2

!!! info "Source"
    Walkthrough lives at [`ansible/README.md`](https://github.com/tyson-swetnam/epihack-2026/blob/main/ansible/README.md).
    The post-EpiHack audit is at [`plan/ANSIBLE-AUDIT-2026-05-23.md`](https://github.com/tyson-swetnam/epihack-2026/blob/main/plan/ANSIBLE-AUDIT-2026-05-23.md).

```bash
cd ansible
cp inventory.example.yml inventory.yml          # edit ansible_host
cp group_vars/all.vault.example.yml group_vars/all.vault.yml
ansible-vault encrypt group_vars/all.vault.yml
ansible-galaxy install -r requirements.yml
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

Roles applied in order: `common → node → python → postgres → repo →
claude_code → mcp_servers → ducklake → mongodb → fastapi → app → nginx`.

See the [audit](https://github.com/tyson-swetnam/epihack-2026/blob/main/plan/ANSIBLE-AUDIT-2026-05-23.md)
for the post-EpiHack tightening pass.
