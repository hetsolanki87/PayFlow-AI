from pydantic import BaseModel, EmailStr, Field
class ClientCreate(BaseModel):
    name: str = Field(min_length=1,max_length=160)
    email: EmailStr
class InvoiceCreate(BaseModel):
    client_id: int
    description: str = Field(min_length=1,max_length=2000)
    amount: float = Field(gt=0,le=1000000)
    currency: str = Field(default='USD',pattern='^[A-Z]{3}$')
    due_date: str
class Prompt(BaseModel):
    text: str = Field(min_length=3,max_length=3000)
