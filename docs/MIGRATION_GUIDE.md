# SLMEducator Migration Guide

## Encryption Key Migration

### Background

In the latest update, we've fixed a critical security issue where the encryption key was regenerated on every application restart. This caused encrypted data to become unreadable after restarts.

### What Changed

**Before**: Encryption key was generated using:
```python
ENCRYPTION_KEY = os.getenv('SLM_ENCRYPTION_KEY', Fernet.generate_key())
```

**After**: Encryption key is now persistent:
```python
from .security_utils import get_or_create_encryption_key
ENCRYPTION_KEY = get_or_create_encryption_key()
```

The key is now stored in `~/.slm_educator/encryption.key` with restricted permissions (0o600).

### Migration Steps

#### For New Installations

No action required. The encryption key will be automatically generated on first run.

#### For Existing Installations

> [!WARNING]
> **Data Loss Risk**: If you have existing encrypted data and don't migrate properly, it will become unreadable.

**Option 1: Fresh Start (Recommended for Development)**
1. Backup your database: `cp slm_educator.db slm_educator.db.backup`
2. Delete the database: `rm slm_educator.db`
3. Restart the application - it will create a new database with the new encryption key

**Option 2: Manual Migration (For Production)**

If you have the old encryption key stored in an environment variable:

1. **Backup your database**:
   ```bash
   cp slm_educator.db slm_educator.db.backup
   ```

2. **Export your old encryption key**:
   ```bash
   echo $SLM_ENCRYPTION_KEY > old_encryption_key.txt
   ```

3. **Run the migration script**:
   ```bash
   python scripts/migrate_encryption_key.py
   ```

4. **Verify the migration**:
   - Login to the application
   - Check that AI configurations are still accessible
   - Verify encrypted content can be read

**Option 3: No Encrypted Data**

If you haven't stored any sensitive data (API keys in database, encrypted content):
1. Simply restart the application
2. The new encryption key will be generated automatically
3. Re-enter any API keys in the settings

### What Data is Encrypted?

The following data types use encryption:
- AI Model API keys stored in database
- Content metadata (if marked as sensitive)
- User preferences (if marked as private)

### Troubleshooting

**Problem**: "Unable to decrypt data" errors after update

**Solution**:
1. Check if `~/.slm_educator/encryption.key` exists
2. If you have the old key, run the migration script
3. If not, you'll need to re-enter encrypted data

**Problem**: Application won't start after update

**Solution**:
1. Check logs in `logs/` directory
2. Verify `src/core/security_utils.py` exists
3. Ensure you have write permissions to `~/.slm_educator/`

### Environment Variables

The application now supports loading configuration from environment variables via `.env` file.

**Setup**:
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```bash
   # OpenRouter API Configuration
   OPENROUTER_API_KEY=your_actual_api_key_here
   
   # Encryption Key (auto-generated if not set)
   SLM_ENCRYPTION_KEY=your_encryption_key_here
   
   # JWT Secret (auto-generated if not set)
   JWT_SECRET=your_jwt_secret_here
   ```

3. Restart the application

**Priority**: Environment variables take precedence over `env.properties` / `settings.properties`.

### Security Best Practices

1. **Never commit `.env` file** - It's already in `.gitignore`
2. **Never commit `env.properties` or `settings.properties` with real API keys**
3. **Backup your encryption key** - Store it securely
4. **Rotate keys periodically** - Use the migration script
5. **Restrict file permissions** - `chmod 600 .env`

### Getting Help

If you encounter issues during migration:
1. Check the logs in `logs/` directory
2. Review the error messages carefully
3. Ensure all dependencies are installed: `pip install -r requirements.txt`
4. Create an issue on GitHub with:
   - Error message
   - Steps to reproduce
   - Your environment (OS, Python version)

---

## JWT Secret Migration

### Background

JWT secret was previously regenerated on every service restart, causing all users to be logged out.

### What Changed

JWT secret is now persistent and stored in `~/.slm_educator/jwt.secret`.

### Migration Steps

**For All Users**:
1. Restart the application
2. All users will need to log in again (one-time)
3. After this, sessions will persist across restarts

**No data migration required** - JWT tokens are short-lived and will naturally expire.

---

## Summary

| Change | Impact | Action Required |
|--------|--------|-----------------|
| Encryption Key | High | Backup data, run migration if needed |
| JWT Secret | Low | Users re-login once |
| Environment Variables | Medium | Create `.env` file |
| Settings Service | Low | None - backward compatible |

**Estimated Migration Time**: 5-15 minutes
