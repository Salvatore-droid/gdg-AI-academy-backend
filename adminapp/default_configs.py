DEFAULT_CONFIGS = {
    # General Settings
    'PLATFORM_NAME': {
        'value': 'Google AI Learning Platform',
        'description': 'The name of your learning platform',
        'category': 'general',
        'data_type': 'string'
    },
    'SUPPORT_EMAIL': {
        'value': 'support@googleai.com',
        'description': 'Email address for user support',
        'category': 'general',
        'data_type': 'string'
    },
    'MAX_STUDENTS_PER_COURSE': {
        'value': '500',
        'description': 'Maximum number of students allowed per course',
        'category': 'general',
        'data_type': 'integer'
    },
    'DEFAULT_TIMEZONE': {
        'value': 'UTC',
        'description': 'Default timezone for the platform',
        'category': 'general',
        'data_type': 'select',
        'options': ['UTC', 'EST', 'PST', 'IST', 'CET']
    },
    
    # Feature Toggles
    'ENABLE_COMMUNITY_FORUMS': {
        'value': 'true',
        'description': 'Enable discussion forums',
        'category': 'features',
        'data_type': 'boolean'
    },
    'ENABLE_AI_LABS': {
        'value': 'true',
        'description': 'Enable hands-on AI projects',
        'category': 'features',
        'data_type': 'boolean'
    },
    'ENABLE_CERTIFICATES': {
        'value': 'true',
        'description': 'Allow certificate generation',
        'category': 'features',
        'data_type': 'boolean'
    },
    'ALLOW_NEW_REGISTRATIONS': {
        'value': 'true',
        'description': 'Allow new user signups',
        'category': 'features',
        'data_type': 'boolean'
    },
    'ENABLE_PAYMENTS': {
        'value': 'false',
        'description': 'Enable payment processing',
        'category': 'features',
        'data_type': 'boolean'
    },
    
    # Email Settings
    'SMTP_HOST': {
        'value': 'smtp.gmail.com',
        'description': 'SMTP server hostname',
        'category': 'email',
        'data_type': 'string'
    },
    'SMTP_PORT': {
        'value': '587',
        'description': 'SMTP server port',
        'category': 'email',
        'data_type': 'integer'
    },
    'SMTP_USERNAME': {
        'value': '',
        'description': 'SMTP authentication username',
        'category': 'email',
        'data_type': 'string'
    },
    'SMTP_PASSWORD': {
        'value': '',
        'description': 'SMTP authentication password',
        'category': 'email',
        'data_type': 'password'
    },
    'EMAIL_FROM_ADDRESS': {
        'value': 'noreply@googleai.com',
        'description': 'Default sender email address',
        'category': 'email',
        'data_type': 'string'
    },
    
    # Security Settings
    'REQUIRE_2FA_FOR_ADMINS': {
        'value': 'false',
        'description': 'Require two-factor authentication for all admins',
        'category': 'security',
        'data_type': 'boolean'
    },
    'SESSION_TIMEOUT_MINUTES': {
        'value': '30',
        'description': 'Auto-logout inactive users after this many minutes',
        'category': 'security',
        'data_type': 'integer'
    },
    'MAX_LOGIN_ATTEMPTS': {
        'value': '5',
        'description': 'Maximum failed login attempts before lockout',
        'category': 'security',
        'data_type': 'integer'
    },
    'PASSWORD_MIN_LENGTH': {
        'value': '8',
        'description': 'Minimum password length',
        'category': 'security',
        'data_type': 'integer'
    },
    'ENABLE_IP_WHITELIST': {
        'value': 'false',
        'description': 'Enable IP whitelist for admin access',
        'category': 'security',
        'data_type': 'boolean'
    },
    
    # Database Settings
    'BACKUP_INTERVAL_HOURS': {
        'value': '24',
        'description': 'Hours between automatic database backups',
        'category': 'database',
        'data_type': 'integer'
    },
    'KEEP_BACKUP_DAYS': {
        'value': '30',
        'description': 'Number of days to keep backup files',
        'category': 'database',
        'data_type': 'integer'
    },
    'DATABASE_CONNECTION_POOL_SIZE': {
        'value': '10',
        'description': 'Database connection pool size',
        'category': 'database',
        'data_type': 'integer'
    },
    
    # Performance Settings
    'CACHE_TIMEOUT_SECONDS': {
        'value': '300',
        'description': 'Cache timeout in seconds',
        'category': 'performance',
        'data_type': 'integer'
    },
    'API_RATE_LIMIT_PER_MINUTE': {
        'value': '60',
        'description': 'API requests per minute per user',
        'category': 'performance',
        'data_type': 'integer'
    },
    'ENABLE_GZIP_COMPRESSION': {
        'value': 'true',
        'description': 'Enable GZIP compression for responses',
        'category': 'performance',
        'data_type': 'boolean'
    },
    
    # Maintenance Settings
    'MAINTENANCE_MODE': {
        'value': 'false',
        'description': 'Put site in maintenance mode',
        'category': 'maintenance',
        'data_type': 'boolean'
    },
    'MAINTENANCE_MESSAGE': {
        'value': 'Site is under maintenance. Please check back later.',
        'description': 'Message to display during maintenance',
        'category': 'maintenance',
        'data_type': 'text'
    },
}