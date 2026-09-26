# Trellis Installation and Upgrade

Prerequisites: Node.js 18+ and Python 3.9+.

```bash
# Install globally
npm install -g @mindfoldhq/trellis@latest

# Initialize in the project root (first time only)
trellis init -u <your-name>

# Upgrade the CLI and sync Trellis files in this project
trellis upgrade
trellis update

# Run only if `trellis update` reports MIGRATION REQUIRED
trellis update --migrate
```
