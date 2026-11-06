import httpx
from fastapi import HTTPException
from .config import settings
async def token():
    if not settings.paypal_client_id or not settings.paypal_client_secret:
        raise HTTPException(503,'PayPal credentials not configured; set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET')
    async with httpx.AsyncClient(timeout=25) as client:
        r=await client.post(settings.paypal_base_url+'/v1/oauth2/token',auth=(settings.paypal_client_id,settings.paypal_client_secret),data={'grant_type':'client_credentials'})
    if r.is_error: raise HTTPException(502,'PayPal authentication failed: '+r.text[:350])
    return r.json()['access_token']
async def request(method,path,payload=None):
    t=await token()
    async with httpx.AsyncClient(timeout=25) as client:
        r=await client.request(method,settings.paypal_base_url+path,headers={'Authorization':'Bearer '+t,'Content-Type':'application/json','Prefer':'return=representation'},json=payload)
    if r.is_error: raise HTTPException(502,'PayPal error: '+r.text[:650])
    return r.json() if r.content else {}
async def verify_webhook(headers,event):
    if not settings.paypal_webhook_id: raise HTTPException(503,'PAYPAL_WEBHOOK_ID not configured')
    payload={'auth_algo':headers.get('paypal-auth-algo'),'cert_url':headers.get('paypal-cert-url'),'transmission_id':headers.get('paypal-transmission-id'),'transmission_sig':headers.get('paypal-transmission-sig'),'transmission_time':headers.get('paypal-transmission-time'),'webhook_id':settings.paypal_webhook_id,'webhook_event':event}
    if not all(payload.values()): raise HTTPException(400,'Missing PayPal signature headers')
    result=await request('POST','/v1/notifications/verify-webhook-signature',payload)
    if result.get('verification_status')!='SUCCESS': raise HTTPException(400,'Webhook signature invalid')
