import json
import logging
import os
import secrets
from dataclasses import dataclass

from aiohttp import ClientSession
from azure.keyvault.secrets.aio import SecretClient
from azure.keyvault.secrets._models import KeyVaultSecret
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from fastapi import APIRouter
from fastapi import status
from pydantic import BaseModel


logger = logging.getLogger(__name__)
router = APIRouter()


class Question(BaseModel):
    prompt: str


@dataclass
class KvSecretHandler:
    kv_url: str = os.getenv("KV-URL", "")
    secret_name: str = "CHATGPT-API-KEY"

    async def get_secret(self) -> KeyVaultSecret:
        default_credential = DefaultAzureCredential()
        kv_client = SecretClient(
            vault_url=self.kv_url,
            credential=default_credential
            )

        async with kv_client:
            async with default_credential:
                return await kv_client.get_secret(self.secret_name)


@dataclass
class StorageBlobHandler:
    account_url = f"https://{os.getenv('ACCOUNT-NAME', '')}.blob.core.windows.net"

    async def upload_blob(self, blob_answer: bytes) -> None:
        file_name = secrets.token_urlsafe(5)
        default_credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            account_url=self.account_url,
            credential=default_credential
            )

        async with blob_service_client:
            async with default_credential:
                container_client = blob_service_client.get_container_client(
                    container="chatgpt"
                    )

                blob_client = container_client.get_blob_client(
                    blob=f"{file_name}.txt"
                    )

                await blob_client.upload_blob(data=blob_answer)


@dataclass
class ChatGptApiCallHandler:
    async def process_question(self, chatgpt_key: str, prompt: str) -> bytes:
        headers = {
            "Authorization": f"Bearer {chatgpt_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "text-davinci-003",
            "prompt": prompt,
            "max_tokens": 100,
            "temperature": 0
        }
        async with ClientSession(headers=headers) as session:
            async with session.post(
                url="https://api.openai.com/v1/completions",
                data=json.dumps(payload)
            ) as response:
                return await response.read()


@router.post("/chatgpt", status_code=status.HTTP_201_CREATED)
async def send_question(question: Question) -> None:
    chatgpt_key = await KvSecretHandler().get_secret()
    chatgpt_response = await ChatGptApiCallHandler().process_question(
        chatgpt_key.value,question.prompt
        )
    await StorageBlobHandler().upload_blob(chatgpt_response)
