import logging
from app import create_app

mm_app = create_app("production")

if __name__ == "__main__":
  gunicorn_logger = logging.getLogger("gunicorn.error")
  mm_app.logger.setLevel(gunicorn_logger.level)
  mm_app.logger.handlers = gunicorn_logger
  mm_app.run(host = "0.0.0.0", port = 5000, debug = True)
