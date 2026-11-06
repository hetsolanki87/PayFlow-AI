from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str = 'sqlite:///./payflow.db'
    paypal_client_id: str = ''
    paypal_client_secret: str = ''
    paypal_webhook_id: str = ''
    paypal_base_url: str = 'https://api-m.sandbox.paypal.com'
    openai_api_key: str = ''
    openai_model: str = 'gpt-4o-mini'
    cors_origins: str = 'http://localhost:4200'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
settings = Settings()
