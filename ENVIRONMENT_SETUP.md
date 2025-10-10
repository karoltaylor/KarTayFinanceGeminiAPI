# Environment Configuration Guide

This project supports multiple environment configurations to easily switch between local development and production databases.

## Available Environments

- **local**: Uses local MongoDB instance (config.local.env)
- **production**: Uses AWS MongoDB Atlas cluster (config.production.env)

## Configuration Files

### `config.local.env` - Local Development
```
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DATABASE=finance_tracking
```

### `config.production.env` - Production (AWS MongoDB Atlas)
```
MONGODB_URL=
MONGODB_DATABASE=finance_tracking
```

## Usage

### Start with Local Database (Default)
```bash
python start_api.py
# or explicitly
python start_api.py --env local
```

### Start with Production Database
```bash
python start_api.py --env production
```

### Additional Options
```bash
# Custom port
python start_api.py --env production --port 8080

# Custom host
python start_api.py --env local --host 127.0.0.1

# Disable auto-reload (for production)
python start_api.py --env production --no-reload

# Get help
python start_api.py --help
```

## Adding New Environments

1. Create a new config file: `config.{env_name}.env`
2. Add your MongoDB connection string and other settings
3. Run: `python start_api.py --env {env_name}`

Example:
```bash
# Create config.staging.env
MONGODB_URL=mongodb+srv://user:pass@staging-cluster.mongodb.net/
MONGODB_DATABASE=finance_tracking_staging

# Use it
python start_api.py --env staging
```

## Security Notes

- **Never commit `config.production.env`** to version control (already in .gitignore)
- Keep your MongoDB credentials secure
- Use environment-specific databases to avoid mixing test and production data
- For production deployments, consider using environment variables instead of files

## Troubleshooting

### "Environment file not found"
Make sure the config file exists:
- `config.local.env` for local environment
- `config.production.env` for production environment

### Connection Issues
- Verify your MongoDB connection string is correct
- For Atlas: Check if your IP is whitelisted
- For local: Ensure MongoDB is running locally

### Check Available Environments
```bash
python start_api.py --help
```
This will show all available environment options.
