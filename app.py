# Legacy file - please use run.py instead
# This file is kept for backward compatibility only

import os
from app import create_app

# Create app instance
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)