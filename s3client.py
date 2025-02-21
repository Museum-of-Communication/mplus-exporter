import boto3
import botocore


class S3Client:
    """Wrapper for boto3"""

    def __init__(
        self,
        region_name,
        endpoint_url,
        bucket_name,
        access_key,
        secret_key,
        key_prefix="",
    ):
        session = boto3.session.Session()
        self.client = session.client(
            "s3",
            region_name=region_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.BUCKET = bucket_name
        self.KEY_PREFIX = key_prefix

    def checkKey(self, key: str) -> bool:
        """Returns True if and only if a given key was found by client. Any exceptions result in False"""

        try:
            response = self.client.head_object(
                Bucket=self.BUCKET, Key=self.__prefixKey(key)
            )
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                return True
        except botocore.exceptions.ClientError:
            return False
        return False

    def putObject(self, key: str, object, contentType: str):
        """Saves object as bytes with key to S3"""
        self.client.put_object(
            Bucket=self.BUCKET,
            Key=self.__prefixKey(key),
            Body=object,
            ContentType=contentType,
        )

    def getObjectString(self, key: str) -> str:
        """Returns object by key decoded as a string"""
        response = self.client.get_object(Bucket=self.BUCKET, Key=self.__prefixKey(key))
        return response["Body"].read().decode("utf-8")  # Decode bytes to string

    def __prefixKey(self, key: str) -> str:
        return f"{self.KEY_PREFIX}/{key}"
