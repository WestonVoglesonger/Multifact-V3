# Command Line Interface

SNC provides a powerful command-line interface for managing your projects.

## Basic Commands

### init

Initialize a new SNC project:

```bash
snc init [--db-url URL] [--openai-key KEY] [--groq-key KEY]
```

Options:

- `--db-url`: Database URL (default: sqlite:///snc.db)
- `--openai-key`: OpenAI API key
- `--groq-key`: Groq API key

### validate

Validate your configuration:

```bash
snc validate [--env-file FILE]
```

Options:

- `--env-file`: Path to .env file (default: .env)

## Configuration Management

### config set

Set a configuration value:

```bash
snc config set KEY VALUE [--env-file FILE]
```

Example:

```bash
snc config set LOG_LEVEL DEBUG
snc config set DATABASE_URL postgresql://user:pass@localhost/db
```

### config get

Get configuration value(s):

```bash
snc config get [KEY] [--env-file FILE]
```

Example:

```bash
snc config get  # Show all values
snc config get LOG_LEVEL  # Show specific value
```

### config backup

Backup your configuration:

```bash
snc config backup [--env-file FILE] [--output FILE]
```

Options:

- `--output`: Output file (default: snc_config_backup.json)

### config restore

Restore configuration from backup:

```bash
snc config restore BACKUP_FILE [--env-file FILE]
```

## Analysis Tools

### analyze

Analyze a narrative document for potential issues:

```bash
snc analyze PATH
```

Example:

```bash
snc analyze narrative.txt
```

### dependencies

Analyze and display token dependencies:

```bash
snc dependencies PATH [--format FORMAT]
```

Options:

- `--format`: Output format (text, json, or dot)

Example:

```bash
snc dependencies narrative.txt --format dot | dot -Tpng > deps.png
```

## Token Management

### list-tokens

List available token types:

```bash
snc list-tokens [TYPE]
```

Example:

```bash
snc list-tokens  # List all types
snc list-tokens Component  # Show Component details
```

## Interactive Tools

### repl

Start an interactive REPL session:

```bash
snc repl
```

This opens an interactive session where you can:

- Test token generation
- Try different narratives
- Debug issues

## Utility Commands

### version

Show SNC version information:

```bash
snc version
```

## Environment Variables

SNC uses the following environment variables:

- `DATABASE_URL`: Database connection URL
- `OPENAI_API_KEY`: OpenAI API key
- `GROQ_API_KEY`: Groq API key
- `LOG_LEVEL`: Logging level
- `LOG_FILE`: Log file path

These can be set in your `.env` file or using the `config set` command.
