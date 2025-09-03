from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import MonthlyData, Expense
from datetime import datetime
from decimal import Decimal
import json
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.shortcuts import get_object_or_404
from collections import defaultdict

def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'financije/login.html', {'error': 'Krivi podaci'})
    return render(request, 'financije/login.html')


def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def home(request):
    return render(request, 'financije/home.html')




@login_required
def dashboard(request):
    selected_month = request.GET.get("month")
    if not selected_month:
        selected_month = datetime.now().strftime("%Y-%m")

    monthly_data, created = MonthlyData.objects.get_or_create(
        user=request.user, month=selected_month
    )

    if request.method == "POST":
        action = request.POST.get("action")
        month = request.POST.get("month", selected_month)

        monthly_data, created = MonthlyData.objects.get_or_create(
            user=request.user, month=month
        )

        if action == "prihodi":
            iznos = request.POST.get("prihodi", "0")
            monthly_data.income = Decimal(iznos or "0")
            monthly_data.save()

        elif action == "cilj":
            iznos = request.POST.get("cilj", "0")
            monthly_data.goal = Decimal(iznos or "0")
            monthly_data.save()

        elif action == "trosak":
            iznos = request.POST.get("iznos", "0")
            if request.POST.get("nova_kategorija"):
                kategorija = request.POST.get("nova_kategorija")
            else:
                kategorija = request.POST.get("kategorija")

            Expense.objects.create(
                monthly_data=monthly_data,
                category=kategorija,
                amount=Decimal(iznos or "0"),
            )

        return redirect(f"/dashboard/?month={month}")

    expenses = monthly_data.expenses.all()
    total_expenses = sum(e.amount for e in expenses)
    remaining = monthly_data.income - total_expenses

    
    category_totals = defaultdict(Decimal)
    for e in expenses:
        category_totals[e.category] += e.amount

    categories = list(category_totals.keys())
    amounts = [float(v) for v in category_totals.values()]

    context = {
        "monthly_data": monthly_data,
        "expenses": expenses,
        "income": float(monthly_data.income),
        "total_expenses": float(total_expenses),
        "remaining": float(remaining),
        "selected_month": selected_month,
        "categories": json.dumps(categories),
        "amounts": json.dumps(amounts),
    }
    return render(request, "financije/dashboard.html", context)

@login_required
def history(request):
    data = MonthlyData.objects.filter(user=request.user).order_by("month")
    history = []
    for m in data:
        total_expenses = sum(e.amount for e in m.expenses.all())
        history.append({
            "id": m.id,
            "month": m.month,  
            "income": float(m.income),
            "goal": float(m.goal),
            "expenses": float(total_expenses),
            "status": "ok" if (m.income - total_expenses) >= m.goal else "fail"
        })
    return render(
        request,
        "financije/history.html",
        {
            "history": history,
            "history_json": json.dumps(history),
        },
    )


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            return render(request, "financije/register.html", {"error": "Lozinke se ne podudaraju."})

        if User.objects.filter(username=username).exists():
            return render(request, "financije/register.html", {"error": "Korisničko ime već postoji."})

        user = User.objects.create_user(username=username, password=password1)
        user.save()
        return redirect("login")

    return render(request, "financije/register.html")


@login_required
def edit_month(request, pk):
    month_data = get_object_or_404(MonthlyData, pk=pk, user=request.user)
    if request.method == "POST":
        try:
            month_data.income = Decimal(request.POST.get("income", month_data.income))
            month_data.goal = Decimal(request.POST.get("goal", month_data.goal))
            month_data.save()
            messages.success(request, "Mjesec uspješno ažuriran")
            return redirect("history")
        except Exception as e:
            messages.error(request, f"Greška: {e}")
    return render(request, "financije/edit_month.html", {"month_data": month_data})


@login_required
def delete_month(request, pk):
    month_data = get_object_or_404(MonthlyData, pk=pk, user=request.user)
    if request.method == "POST":
        month_data.delete()
        messages.success(request, "Mjesec uspješno obrisan")
        return redirect("history")
    return render(request, "financije/delete_month.html", {"month_data": month_data})



@login_required
def export_pdf(request, pk):
    month_data = get_object_or_404(MonthlyData, pk=pk, user=request.user)
    expenses = month_data.expenses.all()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{month_data.month}_report.pdf"'

    
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"Izvještaj za {month_data.month}")
    y -= 40

    p.setFont("Helvetica", 12)
    total_expenses = sum(e.amount for e in expenses)
    remaining = month_data.income - total_expenses
    status = "Ostvaren" if remaining >= month_data.goal else "Nije ostvaren"

    p.drawString(50, y, f"Prihod: {month_data.income} EUR")
    y -= 20
    p.drawString(50, y, f"Cilj: {month_data.goal} EUR")
    y -= 20
    p.drawString(50, y, f"Ukupni troškovi: {total_expenses} EUR")
    y -= 20
    p.drawString(50, y, f"Preostalo: {remaining} EUR")
    y -= 20
    p.drawString(50, y, f"Status: {status}")
    y -= 40

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Troškovi:")
    y -= 25
    p.setFont("Helvetica", 12)
    for e in expenses:
        p.drawString(60, y, f"- {e.category}: {e.amount} EUR")
        y -= 20
        if y < 50:  
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 12)

    p.showPage()
    p.save()

    return response

