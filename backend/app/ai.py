import json,re
from datetime import date,timedelta
import httpx
from .config import settings
async def draft_invoice(text):
    if settings.openai_api_key:
        async with httpx.AsyncClient(timeout=30) as client:
            resp=await client.post('https://api.openai.com/v1/chat/completions',headers={'Authorization':'Bearer '+settings.openai_api_key},json={'model':settings.openai_model,'response_format':{'type':'json_object'},'messages':[{'role':'system','content':'Extract invoice details as JSON with keys description, amount (number), currency (ISO 4217), due_date (YYYY-MM-DD). Never invent a recipient. If no amount specified return amount 0. Default currency USD and due date 7 days from '+str(date.today())+'.'},{'role':'user','content':text}]})
        resp.raise_for_status()
        result=json.loads(resp.json()['choices'][0]['message']['content'])
        return {'description':str(result.get('description') or text),'amount':float(result.get('amount') or 0),'currency':str(result.get('currency') or 'USD').upper(),'due_date':str(result.get('due_date') or date.today()+timedelta(days=7)),'mode':'AI'}
    amounts=re.findall(r'(?:\$|USD\s*)(\d+(?:\.\d{1,2})?)',text,re.I)
    if not amounts: amounts=re.findall(r'\b(\d+(?:\.\d{1,2})?)\b',text)
    return {'description':text,'amount':float(amounts[0]) if amounts else 0,'currency':'USD','due_date':str(date.today()+timedelta(days=7)),'mode':'fallback parser (configure OPENAI_API_KEY for AI)'}
