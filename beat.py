from app import celery

if __name__ == "__main__":
    celery.start(argv=["beat", "-A", "app:celery", "-l", "info"])