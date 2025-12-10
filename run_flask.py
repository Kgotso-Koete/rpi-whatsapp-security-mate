from app import create_app
from app import config

application = create_app()
config.init_logging()

if __name__ == '__main__':
    application.run(debug=True, host='0.0.0.0', port=52961, threaded=True)




