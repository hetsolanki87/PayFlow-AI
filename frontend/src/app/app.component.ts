import {Component,OnInit} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FormsModule} from '@angular/forms';
import {HttpClient} from '@angular/common/http';
interface Client {id:number;name:string;email:string}
interface Invoice {id:number;client_id:number;client_name:string;client_email:string;description:string;amount:number;currency:string;due_date:string;status:string;paypal_url:string|null;paypal_invoice_id:string|null}
@Component({selector:'app-root',standalone:true,imports:[CommonModule,FormsModule],templateUrl:'./app.component.html'})
export class AppComponent implements OnInit {
 api= (window as any).__PAYFLOW_API__ || 'http://localhost:8000'; tab='dashboard';busy=false;error='';message='';clients:Client[]=[];invoices:Invoice[]=[];
 dashboard={total_invoices:0,paid_amount:0,outstanding_amount:0,paid_count:0};insights:string[]=[];
 newClient={name:'',email:''};newInvoice={client_id:0,description:'',amount:0,currency:'USD',due_date:''};prompt='Create a $200 invoice for website design, due in 7 days';aiMode='';
 constructor(private http:HttpClient){}
 ngOnInit(){this.newInvoice.due_date=new Date(Date.now()+7*86400000).toISOString().slice(0,10);this.refresh()}
 refresh(){this.http.get<Client[]>(this.api+'/clients').subscribe({next:x=>{this.clients=x;if(!this.newInvoice.client_id&&x.length)this.newInvoice.client_id=x[0].id},error:e=>this.fail(e)});this.http.get<Invoice[]>(this.api+'/invoices').subscribe({next:x=>this.invoices=x,error:e=>this.fail(e)});this.http.get<any>(this.api+'/dashboard').subscribe({next:x=>this.dashboard=x,error:e=>this.fail(e)});this.http.get<any>(this.api+'/ai/insights').subscribe({next:x=>this.insights=x.insights,error:e=>this.fail(e)})}
 fail(e:any){this.busy=false;this.error=e?.error?.detail||e?.message||'Request failed'}
 clear(){this.error='';this.message=''}
 addClient(){this.clear();this.busy=true;this.http.post(this.api+'/clients',this.newClient).subscribe({next:()=>{this.busy=false;this.newClient={name:'',email:''};this.message='Client added';this.refresh()},error:e=>this.fail(e)})}
 addInvoice(){this.clear();this.busy=true;this.http.post(this.api+'/invoices',this.newInvoice).subscribe({next:()=>{this.busy=false;this.message='Draft saved. Review before sending.';this.tab='invoices';this.refresh()},error:e=>this.fail(e)})}
 draft(){this.clear();this.busy=true;this.http.post<any>(this.api+'/ai/draft',{text:this.prompt}).subscribe({next:x=>{this.busy=false;this.newInvoice={...this.newInvoice,description:x.description,amount:x.amount,currency:x.currency,due_date:x.due_date};this.aiMode=x.mode;this.tab='create';this.message='Draft generated. Verify the amount, recipient, and due date before saving.'},error:e=>this.fail(e)})}
 send(i:Invoice){if(!confirm('Send invoice #'+i.id+' to '+i.client_email+' through PayPal Sandbox?'))return;this.clear();this.busy=true;this.http.post(this.api+'/invoices/'+i.id+'/send',{}).subscribe({next:()=>{this.busy=false;this.message='Invoice sent to PayPal sandbox';this.refresh()},error:e=>this.fail(e)})}
 sync(i:Invoice){this.clear();this.busy=true;this.http.post(this.api+'/invoices/'+i.id+'/sync',{}).subscribe({next:()=>{this.busy=false;this.message='Status refreshed from PayPal';this.refresh()},error:e=>this.fail(e)})}
}
