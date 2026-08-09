import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Uses the docker-compose service name "mysql" as the host so this resolves
# correctly inside the Docker network. Falls back to an env var so it can
# still be overridden for local (non-docker) runs.
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@mysql:3306/bank")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)