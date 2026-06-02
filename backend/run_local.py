import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ['LOCAL_MODE'] = 'true'

from lambda_function import app

if __name__ == '__main__':
    print('Starting local API server at http://localhost:5000')
    app.run(debug=True, port=5000, host='0.0.0.0')
