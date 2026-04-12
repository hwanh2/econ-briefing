from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://briefing:briefing@postgres:5432/briefing")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    nextauth_secret: str = os.getenv("NEXTAUTH_SECRET", "change-me")


settings = Settings()
