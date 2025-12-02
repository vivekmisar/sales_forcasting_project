from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
import json

# Data processing and charting libraries
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# This view now handles the homepage.
def home_view(request):
    return render(request, 'home.html')

# --- THIS IS THE CORRECTED LOGIN LOGIC ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard') # If user is already logged in, send them to the dashboard

    if request.method == 'POST':
        # Get the username and password from the form
        username_from_form = request.POST.get('username')
        password_from_form = request.POST.get('password')

        # Use Django's authenticate function to check if credentials are valid
        user = authenticate(request, username=username_from_form, password=password_from_form)

        if user is not None:
            # If the user is valid, log them in. This creates the session.
            login(request, user)
            return redirect('dashboard') # Redirect to the dashboard upon successful login
        else:
            # If credentials are bad, show an error message.
            messages.error(request, 'Invalid username or password. Please try again.')
            return redirect('login')

    return render(request, 'login.html')

# --- THIS IS THE NEW, FUNCTIONAL REGISTRATION LOGIC ---
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        # --- Validation ---
        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('register')

        # If all checks pass, create the new user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        messages.success(request, 'Registration successful! You can now log in.')
        return redirect('login')

    return render(request, 'register.html')


# This logs the user out and redirects them.
def logout_view(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('login')

@login_required(login_url='login')
def dashboard_view(request):
    # Initialize context with default values
    context = {
        'total_revenue': 'N/A',
        'total_orders': '0',
        'average_order_value': 'N/A',
        'best_selling_product_line': 'N/A',
        'results_exist': False,
        'monthly_trend_chart_html': '',
        'product_performance_chart_html': '',
        'sales_trend_chart_html': '',
        'product_analysis_chart_html': '',
        'yearly_comparison_chart_html': '',
        'top_products_chart_html': '',
        'sales_summary': '',
        'raw_data_table': ''
    }

    # Check if we have stored data in session
    if 'sales_data' in request.session:
        try:
            # Restore data from session
            sales_data = request.session['sales_data']
            context.update(sales_data)
            context['results_exist'] = True
        except Exception as e:
            # If session data is corrupted, clear it
            del request.session['sales_data']
            messages.warning(request, "Session data was corrupted. Please upload your CSV file again.")

    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, "No file was uploaded. Please select a CSV file.")
            return redirect('dashboard')

        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'This is not a CSV file. Please upload a valid .csv file.')
            return redirect('dashboard')

        try:
            decoded_file = csv_file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(decoded_file))

            # --- VALIDATION BLOCK ---
            column_mappings = {
                'SALES': ['SALES', 'Sales', 'sales', 'Revenue', 'revenue', 'Product_sold', 'product_sold'],
                'ORDERDATE': ['ORDERDATE', 'OrderDate', 'orderdate', 'Date', 'date'],
                'PRODUCTLINE': ['PRODUCTLINE', 'ProductLine', 'productline', 'Product', 'product', 'Product_name', 'product_name']
            }

            df_columns = list(df.columns)
            found_columns = {}
            missing_requirements = []

            for req_col, alternatives in column_mappings.items():
                match = next((col for col in df_columns if col in alternatives), None)
                if match:
                    found_columns[req_col] = match
                else:
                    missing_requirements.append(f"{req_col} (or {', '.join(alternatives)})")

            if missing_requirements:
                messages.error(request, f"Missing required columns. Please ensure your CSV has: {', '.join(missing_requirements)}")
                return redirect('dashboard')
            
            # Rename columns to standard internal names
            df.rename(columns={
                found_columns['SALES']: 'Total Revenue',
                found_columns['ORDERDATE']: 'Date',
                found_columns['PRODUCTLINE']: 'Product Line'
            }, inplace=True)

            # Data Preparation
            df['Date'] = pd.to_datetime(df['Date'])
            df['Year'] = df['Date'].dt.year
            df['Month'] = df['Date'].dt.month
            df['MonthName'] = df['Date'].dt.strftime('%B')

            # --- 1. CALCULATE KPIs ---
            total_revenue = df['Total Revenue'].sum()
            # Check if ORDERNUMBER exists (it's not renamed, so check original column name)
            has_order_number = 'ORDERNUMBER' in df.columns
            total_orders = df['ORDERNUMBER'].nunique() if has_order_number else len(df)
            average_order_value = total_revenue / total_orders if total_orders > 0 else 0
            best_selling_product_line = df.groupby('Product Line')['Total Revenue'].sum().idxmax()

            context['total_revenue'] = f"${total_revenue:,.2f}"
            context['total_orders'] = f"{total_orders:,}"
            context['average_order_value'] = f"${average_order_value:,.2f}"
            context['best_selling_product_line'] = best_selling_product_line

            # --- 2. GENERATE SALES SUMMARY TABLE ---
            summary_html = df.describe(include='all').to_html(
                classes="w-full text-sm text-left text-gray-300",
                border=0
            )
            context['sales_summary'] = summary_html

            # --- 3. GENERATE RAW DATA TABLE (first 100 rows) ---
            raw_data_html = df.head(100).to_html(
                classes="w-full text-sm text-left text-gray-300",
                border=0,
                table_id="raw-data-table"
            )
            context['raw_data_table'] = raw_data_html

            # --- 4. GENERATE MONTHLY TREND LINE CHART ---
            monthly_sales = df.groupby(df['Date'].dt.to_period('M'))['Total Revenue'].sum().reset_index()
            monthly_sales['Date'] = monthly_sales['Date'].dt.to_timestamp()
            fig_line = px.line(
                monthly_sales, 
                x='Date', 
                y='Total Revenue', 
                title='Monthly Revenue Trend',
                markers=True,
                line_shape='spline'
            )
            fig_line.update_traces(line_color='#38bdf8', line_width=3)
            fig_line.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#f8fafc',
                title_font_size=18,
                xaxis_title='Month',
                yaxis_title='Total Revenue ($)',
                hovermode='x unified'
            )
            context['monthly_trend_chart_html'] = fig_line.to_html(full_html=False, include_plotlyjs=False)

            # --- 5. GENERATE PRODUCT PERFORMANCE BAR CHART ---
            product_sales = df.groupby('Product Line')['Total Revenue'].sum().sort_values(ascending=False).reset_index()
            fig_bar = px.bar(
                product_sales, 
                x='Product Line', 
                y='Total Revenue', 
                title='Sales by Product Line',
                color='Product Line',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_bar.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#f8fafc',
                title_font_size=18,
                xaxis_title='Product Line',
                yaxis_title='Total Revenue ($)',
                showlegend=False
            )
            context['product_performance_chart_html'] = fig_bar.to_html(full_html=False, include_plotlyjs=False)

            # --- 6. GENERATE DETAILED SALES TREND CHART (with multiple metrics) ---
            if has_order_number:
                monthly_detailed = df.groupby(df['Date'].dt.to_period('M')).agg({
                    'Total Revenue': 'sum',
                    'ORDERNUMBER': 'nunique'
                }).reset_index()
            else:
                monthly_detailed = df.groupby(df['Date'].dt.to_period('M')).agg({
                    'Total Revenue': 'sum'
                }).reset_index()
                monthly_detailed['ORDERNUMBER'] = df.groupby(df['Date'].dt.to_period('M')).size().values
            monthly_detailed['Date'] = monthly_detailed['Date'].dt.to_timestamp()
            monthly_detailed.columns = ['Date', 'Revenue', 'Orders']
            
            fig_trends = make_subplots(specs=[[{"secondary_y": True}]])
            fig_trends.add_trace(
                go.Scatter(x=monthly_detailed['Date'], y=monthly_detailed['Revenue'], 
                          name='Revenue', line=dict(color='#38bdf8', width=3)),
                secondary_y=False,
            )
            fig_trends.add_trace(
                go.Scatter(x=monthly_detailed['Date'], y=monthly_detailed['Orders'], 
                          name='Orders', line=dict(color='#10b981', width=3)),
                secondary_y=True,
            )
            fig_trends.update_xaxes(title_text="Month")
            fig_trends.update_yaxes(title_text="Revenue ($)", secondary_y=False)
            fig_trends.update_yaxes(title_text="Number of Orders", secondary_y=True)
            fig_trends.update_layout(
                title_text="Sales Trends: Revenue & Orders Over Time",
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#f8fafc',
                title_font_size=18
            )
            context['sales_trend_chart_html'] = fig_trends.to_html(full_html=False, include_plotlyjs=False)

            # --- 7. GENERATE PRODUCT ANALYSIS (Pie Chart + Bar Chart) ---
            if has_order_number:
                product_analysis = df.groupby('Product Line').agg({
                    'Total Revenue': 'sum',
                    'ORDERNUMBER': 'nunique'
                }).reset_index()
            else:
                product_analysis = df.groupby('Product Line').agg({
                    'Total Revenue': 'sum'
                }).reset_index()
                product_analysis['ORDERNUMBER'] = df.groupby('Product Line').size().values
            product_analysis.columns = ['Product Line', 'Revenue', 'Orders']
            product_analysis = product_analysis.sort_values('Revenue', ascending=False)
            
            fig_pie = px.pie(
                product_analysis,
                values='Revenue',
                names='Product Line',
                title='Revenue Distribution by Product Line',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#f8fafc',
                title_font_size=18
            )
            context['product_analysis_chart_html'] = fig_pie.to_html(full_html=False, include_plotlyjs=False)

            # --- 8. GENERATE YEARLY COMPARISON CHART ---
            if len(df['Year'].unique()) > 1:
                yearly_sales = df.groupby('Year')['Total Revenue'].sum().reset_index()
                fig_yearly = px.bar(
                    yearly_sales,
                    x='Year',
                    y='Total Revenue',
                    title='Yearly Revenue Comparison',
                    color='Total Revenue',
                    color_continuous_scale='Blues'
                )
                fig_yearly.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f8fafc',
                    title_font_size=18,
                    showlegend=False
                )
                context['yearly_comparison_chart_html'] = fig_yearly.to_html(full_html=False, include_plotlyjs=False)
            else:
                context['yearly_comparison_chart_html'] = '<p class="text-gray-400">Multiple years of data required for comparison.</p>'

            # --- 9. GENERATE TOP PRODUCTS CHART ---
            if has_order_number:
                top_products = df.groupby('Product Line').agg({
                    'Total Revenue': 'sum',
                    'ORDERNUMBER': 'nunique'
                }).reset_index()
            else:
                top_products = df.groupby('Product Line').agg({
                    'Total Revenue': 'sum'
                }).reset_index()
                top_products['ORDERNUMBER'] = df.groupby('Product Line').size().values
            top_products.columns = ['Product Line', 'Revenue', 'Orders']
            top_products['Avg Order Value'] = top_products['Revenue'] / top_products['Orders']
            top_products = top_products.sort_values('Revenue', ascending=True).tail(10)
            
            fig_top = go.Figure()
            fig_top.add_trace(go.Bar(
                y=top_products['Product Line'],
                x=top_products['Revenue'],
                orientation='h',
                name='Revenue',
                marker_color='#38bdf8'
            ))
            fig_top.update_layout(
                title='Top Products by Revenue',
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#f8fafc',
                title_font_size=18,
                xaxis_title='Revenue ($)',
                yaxis_title='Product Line'
            )
            context['top_products_chart_html'] = fig_top.to_html(full_html=False, include_plotlyjs=False)

            context['results_exist'] = True

            # Store in session (convert to JSON-serializable format)
            session_data = {
                'total_revenue': context['total_revenue'],
                'total_orders': context['total_orders'],
                'average_order_value': context['average_order_value'],
                'best_selling_product_line': context['best_selling_product_line'],
                'monthly_trend_chart_html': context['monthly_trend_chart_html'],
                'product_performance_chart_html': context['product_performance_chart_html'],
                'sales_trend_chart_html': context['sales_trend_chart_html'],
                'product_analysis_chart_html': context['product_analysis_chart_html'],
                'yearly_comparison_chart_html': context['yearly_comparison_chart_html'],
                'top_products_chart_html': context['top_products_chart_html'],
                'sales_summary': context['sales_summary'],
                'raw_data_table': context['raw_data_table']
            }
            request.session['sales_data'] = session_data

        except Exception as e:
            messages.error(request, f"An error occurred while processing the file: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return redirect('dashboard')

    return render(request, 'dashboard.html', context)





@login_required(login_url='login')
def profile_view(request):
    return render(request, 'profile.html')


def about_view(request):
    return render(request, 'about.html')


def contact_view(request):
    if request.method == 'POST':
        # Simulate sending email
        name = request.POST.get('name')
        messages.success(request, f"Thanks for reaching out, {name}! We'll be in contact ASAP.")
        return redirect('contact')
    return render(request, 'contact.html')

