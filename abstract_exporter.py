from abc import ABC, abstractmethod
import os
from dotenv import load_dotenv
from s3client import S3Client
from mpluspy import MPlusClient

load_dotenv()


class AbstractExporter(ABC):

    def __init__(self):
        self.s3 = S3Client(
            "config/s3.yml", os.getenv("s3-access-key"), os.getenv("s3-secret-key")
        )
        mplus_auth = (os.getenv("mplus-user"), os.getenv("mplus-pass"))
        self.mplus = MPlusClient("config/mplus.yml", auth=mplus_auth)

    @abstractmethod
    def run_export(self):
        pass
