from datetime import date
from decimal import Decimal
from fastapi import FastAPI,Depends,HTTPException,Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from .db import Base,engine,get_db
from .models import Client,Invoice,WebhookEvent
from .schemas import ClientCreate,InvoiceCreate,Prompt
from .config import settings
from . import paypal,ai
Base.metadata.create_all(bind=engine)
app=FastAPI(title='PayFlow AI API',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=[s.strip() for s in settings.cors_origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
def serialize(inv):
    return {'id':inv.id,'client_id':inv.client_id,'client_name':inv.client.name,'client_email':inv.client.email,'description':inv.description,'amount':float(inv.amount),'currency':inv.currency,'due_date':inv.due_date,'status':inv.status,'paypal_invoice_id':inv.paypal_invoice_id,'paypal_url':inv.paypal_url}
@app.get('/health')
def health(): return {'status':'ok','paypal_configured':bool(settings.paypal_client_id and settings.paypal_client_secret),'ai_configured':bool(settings.openai_api_key)}
@app.get('/clients')
def clients(db:Session=Depends(get_db)):
    return [{'id':c.id,'name':c.name,'email':c.email} for c in db.scalars(select(Client).order_by(Client.id.desc())).all()]
@app.post('/clients',status_code=201)
def create_client(body:ClientCreate,db:Session=Depends(get_db)):
    c=Client(**body.model_dump());db.add(c);db.commit();db.refresh(c);return {'id':c.id,'name':c.name,'email':c.email}
@app.get('/invoices')
def invoices(db:Session=Depends(get_db)):
    return [serialize(i) for i in db.scalars(select(Invoice).order_by(Invoice.id.desc())).all()]
@app.post('/invoices',status_code=201)
def create_invoice(body:InvoiceCreate,db:Session=Depends(get_db)):
    if not db.get(Client,body.client_id):raise HTTPException(404,'Client not found')
    try:
        if date.fromisoformat(body.due_date)<date.today():raise ValueError()
    except ValueError:raise HTTPException(422,'Due date must be a valid current or future YYYY-MM-DD date')
    inv=Invoice(**body.model_dump());db.add(inv);db.commit();db.refresh(inv);return serialize(inv)
@app.post('/ai/draft')
async def ai_draft(body:Prompt):return await ai.draft_invoice(body.text)
@app.post('/invoices/{invoice_id}/send')
async def send_invoice(invoice_id:int,db:Session=Depends(get_db)):
    inv=db.get(Invoice,invoice_id)
    if not inv:raise HTTPException(404,'Invoice not found')
    if inv.status not in ('DRAFT','CREATED'):raise HTTPException(409,'Invoice already sent or finalized')
    if not inv.paypal_invoice_id:
        payload={'detail':{'currency_code':inv.currency,'note':'Invoice from PayFlow AI','payment_term':{'term_type':'DUE_ON_DATE','due_date':inv.due_date}},'invoicer':{'name':{'given_name':'PayFlow','surname':'Business'}},'primary_recipients':[{'billing_info':{'name':{'given_name':inv.client.name[:80]},'email_address':inv.client.email}}],'items':[{'name':inv.description[:200],'quantity':'1','unit_amount':{'currency_code':inv.currency,'value':f'{inv.amount:.2f}'}}]}
        created=await paypal.request('POST','/v2/invoicing/invoices',payload)
        inv.paypal_invoice_id=created['id'];inv.status='CREATED';db.commit()
    await paypal.request('POST',f'/v2/invoicing/invoices/{inv.paypal_invoice_id}/send',{'send_to_recipient':True,'send_to_invoicer':False})
    inv.status='SENT';db.commit()
    return await sync_invoice(invoice_id,db)
@app.post('/invoices/{invoice_id}/sync')
async def sync_invoice(invoice_id:int,db:Session=Depends(get_db)):
    inv=db.get(Invoice,invoice_id)
    if not inv:raise HTTPException(404,'Invoice not found')
    if not inv.paypal_invoice_id:raise HTTPException(409,'Invoice not sent to PayPal')
    data=await paypal.request('GET',f'/v2/invoicing/invoices/{inv.paypal_invoice_id}')
    inv.status=data.get('status',inv.status)
    for link in data.get('links',[]):
        if link.get('rel') in ('payer-view','payer_view'):inv.paypal_url=link.get('href')
    db.commit();db.refresh(inv);return serialize(inv)
@app.post('/webhooks/paypal')
async def webhook(request:Request,db:Session=Depends(get_db)):
    event=await request.json()
    await paypal.verify_webhook(request.headers,event)
    event_id=event.get('id'); event_type=event.get('event_type','')
    if not event_id:raise HTTPException(400,'Missing event ID')
    if db.scalar(select(WebhookEvent).where(WebhookEvent.event_id==event_id)):return {'received':True,'duplicate':True}
    resource=event.get('resource') or {}
    invoice_id=resource.get('invoice_id') or (resource.get('id') if str(resource.get('id','')).startswith('INV') else None)
    inv=db.scalar(select(Invoice).where(Invoice.paypal_invoice_id==invoice_id)) if invoice_id else None
    if inv:
        mapping={'INVOICING.INVOICE.PAID':'PAID','INVOICING.INVOICE.CANCELLED':'CANCELLED','INVOICING.INVOICE.REFUNDED':'REFUNDED','INVOICING.INVOICE.SENT':'SENT'}
        if event_type in mapping:inv.status=mapping[event_type]
    db.add(WebhookEvent(event_id=event_id,event_type=event_type));db.commit()
    return {'received':True}
@app.get('/dashboard')
def dashboard(db:Session=Depends(get_db)):
    invoices=db.scalars(select(Invoice)).all()
    paid=sum((Decimal(i.amount) for i in invoices if i.status=='PAID'),Decimal(0))
    outstanding=sum((Decimal(i.amount) for i in invoices if i.status in ('SENT','UNPAID','PARTIALLY_PAID','OVERDUE')),Decimal(0))
    return {'total_invoices':len(invoices),'paid_amount':float(paid),'outstanding_amount':float(outstanding),'paid_count':sum(i.status=='PAID' for i in invoices),'currency_note':'Totals assume all invoices use the same currency; filter by currency before production reporting.'}
@app.get('/ai/insights')
def insights(db:Session=Depends(get_db)):
    invoices=db.scalars(select(Invoice)).all()
    overdue=[i for i in invoices if i.status in ('SENT','UNPAID','OVERDUE') and i.due_date<str(date.today())]
    return {'insights':[f'{len(overdue)} sent invoice(s) are past their due date.',f'{sum(i.status=="PAID" for i in invoices)} of {len(invoices)} invoices are marked paid.','These insights are deterministic analytics, not ML predictions.'],'overdue_ids':[i.id for i in overdue]}
