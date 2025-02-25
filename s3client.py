import boto3
import botocore
import yaml


class S3Client:
    """Wrapper for boto3"""

    def __init__(self, config_file, access_key, secret_key):
        with open(config_file, "r") as f:
            S3_CONFIG = yaml.load(f, Loader=yaml.FullLoader)

        session = boto3.session.Session()
        self.client = session.client(
            "s3",
            region_name=S3_CONFIG["region-name"],
            endpoint_url=S3_CONFIG["endpoint-url"],
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.BUCKET = S3_CONFIG["bucket-name"]
        self.KEY_PREFIX = S3_CONFIG["key-prefix"]

    def check_key(self, key: str) -> bool:
        """Returns True if and only if a given key was found by client. Any exceptions result in False"""
        try:
            self.client.head_object(Bucket=self.BUCKET, Key=self.__prefix_key(key))
            return True
        except botocore.exceptions.ClientError:
            return False

    def put_object(self, key: str, object, content_type: str):
        """Saves object as bytes with key to S3"""
        self.client.put_object(
            Bucket=self.BUCKET,
            Key=self.__prefix_key(key),
            Body=object,
            ContentType=content_type,
        )

    def get_object_string(self, key: str) -> str:
        """Returns object by key decoded as a string"""
        response = self.client.get_object(
            Bucket=self.BUCKET, Key=self.__prefix_key(key)
        )
        return response["Body"].read().decode("utf-8")  # Decode bytes to string

    def __prefix_key(self, key: str) -> str:
        return f"{self.KEY_PREFIX}/{key}"
