from flask import Flask,request,render_template,session,redirect,url_for,flash
import random
from flask_mail import Message,Mail
import os
from werkzeug.security import check_password_hash,generate_password_hash
import pymysql
import razorpay
from flask import jsonify 
from datetime import datetime, date, time
from werkzeug.utils import secure_filename
import difflib  
con = pymysql.connect(host = "localhost", user = "root", password= "", database="project")
cursor = con.cursor()
app = Flask(__name__)
app.secret_key = 'your-very-secret-key'  

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'hetvisuthar311@gmail.com'
app.config['MAIL_PASSWORD'] = 'izcykjlqumdtlqze'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
razorpay_client = razorpay.Client(auth=("rzp_test_0L2pyQqkJzupt2","lLsJlxExjLJ3ZRVY3zkq0qPU"))
mail = Mail(app)

cateimgpath = "static/uploads/category/"
subcateimgpath = "static/uploads/subcategory/"
packimgpath = "static/uploads/packages/"
feedbackimgpath = "static/uploads/feedback/"

#admin section
@app.route('/admin/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor.execute("SELECT * FROM admin_login WHERE email = %s", (email,))
        admin = cursor.fetchone()

        if admin and admin[2] == password:
            session['admin_id'] = admin[0]
            session['admin_email'] = admin[1]
            session['admin_logged_in'] = True
            flash("Login successful!", "success")
            return render_template("admin/adminlogin.html", redirect_to=url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return render_template("admin/adminlogin.html")

    return render_template("admin/adminlogin.html")
          
@app.route('/admin/adminlogout')
def adminlogout():
    session.pop('admin_id')
    session.pop('admin_email')
    flash("Logged out Successfully!","info")
    return redirect(url_for('adminlogin'))

@app.route('/admin/admineditprofile')
def admineditprofile():
    if not session.get('admin_email'):
        flash("Please login first!")
        return redirect(url_for('adminlogin'))
    email = session.get('admin_email')
    sql = "SELECT * FROM admin_login WHERE email = %s"
    val = (email,)
    cursor.execute(sql,val)
    admin = cursor.fetchone()
    print(admin)
    return render_template("admin/admineditprofile.html",admin=admin)

@app.route('/admin/adminupdateprofile', methods=['POST'])
def adminupdateprofile():
    if not session.get('admin_email'):
        flash("Unauthorized access!", "danger")
        return redirect(url_for('adminlogin'))
    password = request.form['password']
    email = session.get('admin_email')
    sql = "UPDATE admin_login SET password = %s WHERE email = %s"
    val = (password, email)
    cursor.execute(sql, val)
    con.commit()
    flash("Profile updated successfully!", "success")
    return redirect(url_for('adminlogin'))

@app.route('/admin/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        flash("Please login to access the dashboard.")
        return redirect(url_for('adminlogin'))
    
    #total users
    cursor.execute("SELECT COUNT(*) FROM user_reg")
    total_users = cursor.fetchone()[0]

    #total bookings
    cursor.execute("SELECT COUNT(*) FROM booking")
    total_bookings = cursor.fetchone()[0]

    #total packages
    cursor.execute("SELECT COUNT(*) FROM tbl_package")
    total_packages = cursor.fetchone()[0]

    #verified booking
    cursor.execute("SELECT COUNT(*) FROM booking WHERE LOWER(status) = 'confirmed'")
    booking_verified = cursor.fetchone()[0]

    #calculate booking verified percentage
    if total_bookings > 0:
        booking_verified_percent = round((booking_verified / total_bookings)* 100, 2)
    else:
        booking_verified_percent = 0    

    #pending booking
    cursor.execute("SELECT COUNT(*) FROM booking WHERE LOWER(status) = 'pending'")
    pending_bookings = cursor.fetchone()[0]

    #calculate pending percentage
    if total_bookings > 0:
        pending_percent = round((pending_bookings / total_bookings)* 100, 2)
    else:
        pending_percent = 0

    #popular package(This month)
    cursor.execute("""SELECT p.package_name, COUNT(*) AS total FROM booking b JOIN tbl_package p ON 
                   b.package_id = p.package_id WHERE LOWER(b.status) = 'confirmed'
                   AND MONTH(b.travel_date) = MONTH(CURDATE()) AND YEAR(b.travel_date) = YEAR(CURDATE())
                   GROUP BY b.package_id ORDER BY total DESC LIMIT 1""") 
    result = cursor.fetchone()
    popular_package = result[0] if result else "No bookings yet"
    popular_count = result[1] if result else 0

    # progress bar percent
    popular_percent = round((popular_count / total_bookings) * 100, 2) if total_bookings > 0 else 0  

    #blocked users
    cursor.execute("SELECT COUNT(*) FROM user_reg WHERE status = 1") 
    blocked_users = cursor.fetchone()[0]
    
    #blocked users percentage
    if total_users > 0:
        blocked_percent = round((blocked_users / total_users )* 100, 2)
    else:
        blocked_percent = 0    

    #monthly booking
    cursor.execute("""SELECT MONTH(travel_date) AS month, COUNT(*) AS total FROM booking WHERE LOWER(status) = 'confirmed' 
                   GROUP BY MONTH(travel_date) """)    
    monthly_data = cursor.fetchall()

    month_labels = ['Jan','Feb','Mar','Apr','May','Jun','Jul',
                    'Aug','Sep','Oct','Nov','Dec']
    monthly_counts = [0] * 12

    for row in monthly_data:
        month = row[0]
        total = row[1]
        monthly_counts[month - 1] = total

      # Top 5 Packages by Revenue (for Pie Chart)
    cursor.execute("""
    SELECT p.package_name, COUNT(*) AS total_booked
    FROM booking b
    JOIN tbl_package p ON b.package_id = p.package_id
    WHERE LOWER(b.status) = 'confirmed'
    GROUP BY b.package_id
    ORDER BY total_booked DESC
    LIMIT 5""")
    top_packages = cursor.fetchall()

    # Separate data for chart
    top_package_names = [row[0] for row in top_packages]
    top_package_counts = [row[1] for row in top_packages]


    return render_template("admin/dashboard.html",total_users = total_users , 
                           total_bookings = total_bookings,
                           total_packages = total_packages,booking_verified=booking_verified,booking_verified_percent=booking_verified_percent,
                           pending_bookings=pending_bookings,pending_percent=pending_percent,popular_package=popular_package,
                           popular_count=popular_count,
                           popular_percent=popular_percent,blocked_users=blocked_users,blocked_percent=blocked_percent,month_labels=month_labels,monthly_counts=monthly_counts,
                           top_package_names=top_package_names,top_package_counts=top_package_counts)

@app.route('/admin/category')
def category():
    return render_template("admin/category.html")

@app.route("/addcategory",methods = ['POST'])
def addcategory():
    name = request.form['cname']
    image = request.files['image']
    imgpath = os.path.join(cateimgpath,image.filename)
    image.save(imgpath)
    sql = "INSERT INTO `category`(`name`, `image`) VALUES (%s,%s)"
    val = (name,imgpath)
    cursor.execute(sql,val)
    con.commit()
    return redirect('/admin/categorylist')

@app.route('/admin/categorylist')
def categorylist():
    sql = "SELECT * FROM `category` order by category_id DESC"
    cursor.execute(sql)
    category = cursor.fetchall()
    print(category)
    return render_template("admin/categorylist.html",cate = category)

@app.route("/admin/editcategory/<int:id>" , methods = ['GET'])
def editcategory(id):
    sql = "SELECT * FROM `category` WHERE category_id = %s"
    val = (id,)
    cursor.execute(sql,val)
    data = cursor.fetchone()
    print(data)
    return render_template('admin/category_edit.html', data = data)

@app.route("/admin/updatecategory/<int:id>", methods = ['POST'])
def updatecategory(id):
    name = request.form['cname']
    if request.files['image']:
        image = request.files['image']
        imgpath = os.path.join(cateimgpath,image.filename)
        image.save(imgpath)
        sql = "UPDATE `category` SET `name`= %s,`image`= %s WHERE category_id = %s"        
        val = (name,imgpath,id)
    else:
        sql = "UPDATE `category` SET `name`= %s WHERE category_id = %s"
        val = (name,id)
    cursor.execute(sql,val)
    con.commit()
    return redirect('/admin/categorylist')

@app.route("/admin/deletecategory/<int:id>")
def deletecategory(id):
    sql = "DELETE FROM category WHERE category_id = %s"
    val = (id,)
    cursor.execute(sql, val)
    con.commit()
    return redirect('/admin/categorylist')

@app.route('/admin/subcategory')
def subcategory():
    sql = "SELECT * FROM `category` order by category_id DESC"
    cursor.execute(sql)
    category = cursor.fetchall()
    return render_template("admin/subcategory.html",cate = category)

@app.route('/admin/addsubcategory',methods = ['POST'])
def addsubcategory():
    name = request.form['sname']
    location = request.form['slocation']
    image = request.files['image']
    imgpath = os.path.join(subcateimgpath,image.filename)
    image.save(imgpath)
    id = request.form['cateid']
    is_international = int(request.form['is_international'])
    sql = "INSERT INTO `subcategory`(`category_id`, `name`,`location` , `image`, `is_international`) VALUES (%s,%s,%s,%s,%s)"
    val = (id,name,location,imgpath,is_international)
    cursor.execute(sql,val)
    con.commit()
    return redirect('/admin/subcategorylist')

@app.route('/admin/subcategorylist')
def subcategorylist():
    sql = "SELECT a.*,b.name FROM subcategory as a, category as b WHERE a.category_id=b.category_id order by a.subcategory_id DESC"
    cursor.execute(sql)
    subcategory = cursor.fetchall()
    print(subcategory)
    return render_template("admin/subcategorylist.html",subcate = subcategory)

@app.route('/admin/editsubcategory/<int:id>', methods = ['GET'])
def editsubcategory(id):
    sql = "SELECT * FROM `subcategory` WHERE subcategory_id = %s"
    val = (id,)
    cursor.execute(sql,val)
    subcat = cursor.fetchone()
    sql ="SELECT * FROM `category` order by category_id DESC"
    cursor.execute(sql)
    category = cursor.fetchall()
    return render_template('admin/subcategory_edit.html', subcat = subcat, cate = category)

@app.route('/admin/updatesubcategory/<int:id>', methods = ['POST'])
def updatesubcategory(id):
    name = request.form['sname']
    location = request.form['slocation']
    cid = request.form['cateid']

    if request.files['image']:
            image = request.files['image']
            imgpath = os.path.join(subcateimgpath,image.filename)
            image.save(imgpath)
            sql = "UPDATE `subcategory` SET `name`= %s, `location` = %s , `image`= %s , `category_id`= %s WHERE subcategory_id = %s"        
            val = (name,location,imgpath,cid,id)
    else:
            sql = "UPDATE `subcategory` SET `name`= %s, `location` = %s, `category_id`= %s WHERE subcategory_id = %s"         
            val = (name,location,cid,id)
    cursor.execute(sql,val)
    con.commit()
    return redirect('/admin/subcategorylist')

@app.route("/admin/deletesubcategory/<int:id>")
def deletesubcategory(id):
    sql = "DELETE FROM `subcategory` WHERE subcategory_id = %s"
    val = (id,)
    cursor.execute(sql,val)
    con.commit()
    return redirect('/admin/subcategorylist') 

@app.route('/admin/package')
def package():
    sql = "SELECT * FROM `category` order by category_id DESC"
    cursor.execute(sql)
    category = cursor.fetchall()
    sql1 = "SELECT * FROM `subcategory` order by subcategory_id DESC"
    cursor.execute(sql1)
    subcategory = cursor.fetchall()
    return render_template("admin/package.html",subcate = subcategory,cate = category)

@app.route("/admin/addpackage",methods = ['POST'])
def addpackage():
    name = request.form['pname']
    destination = request.form['pdestination']
    duration = request.form['pduration']
    price = request.form['pprice']
    image = request.files['image']
    discription = request.form['pdescription']
    imgpath = os.path.join(packimgpath,image.filename)
    image.save(imgpath)
    subid = request.form['subid']
    catid = request.form['catid']

    is_international = request.form.get('is_international')
    if is_international == '1':
        is_international = 1
    else:
        is_international = 0

    sql = "INSERT INTO `tbl_package`(`package_name`, `package_destination`, `package_duration`, `package_price`, `package_image`, `package_description`,`subcategory_id`,`category_id`,`is_international`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    val = (name,destination,duration,price,imgpath,discription,subid,catid,is_international)
    cursor.execute(sql,val)
    con.commit()
    return redirect('/admin/packagelist')

@app.route('/admin/packagelist')
def packagelist():
    sql = "SELECT a.*,b.name FROM tbl_package as a, subcategory as b WHERE a.subcategory_id=b.subcategory_id order by a.package_id DESC"
    cursor.execute(sql)
    package = cursor.fetchall()
    print(package)
    return render_template("admin/packagelist.html",pack = package)

@app.route("/admin/editpackage/<int:id>", methods = ['GET'])
def editpackage(id):
    sql = "SELECT * FROM `tbl_package` WHERE package_id = %s"
    val = (id,)
    cursor.execute(sql,val)
    data = cursor.fetchone()
    sql = "SELECT * FROM `subcategory` order by subcategory_id DESC"
    cursor.execute(sql)
    subcategory = cursor.fetchall()
    return render_template('admin/package_edit.html', data = data, subcate = subcategory)

@app.route("/admin/updatepackage/<int:id>", methods=['POST'])
def updatepackage(id):
    name = request.form['pname']
    destination = request.form['pdestination']
    duration = request.form['pduration']
    price = request.form['pprice']
    description = request.form['pdescription']
    sid = request.form['subcateid']

    is_international = 1 if request.form.get('is_international') == '1' else 0

    if 'image' in request.files and request.files['image'].filename != '':
        image = request.files['image']
        imgpath = os.path.join(packimgpath, image.filename)
        image.save(imgpath)
        sql = """
            UPDATE `tbl_package`
            SET `package_name`=%s, `package_destination`=%s, `package_duration`=%s,
                `package_price`=%s, `package_image`=%s, `package_description`=%s,
                `subcategory_id`=%s, `is_international`=%s
            WHERE `package_id`=%s
        """
        val = (name, destination, duration, price, imgpath, description, sid, is_international, id)
    else:
        sql = """
            UPDATE `tbl_package`
            SET `package_name`=%s, `package_destination`=%s, `package_duration`=%s,
                `package_price`=%s, `package_description`=%s,
                `subcategory_id`=%s, `is_international`=%s
            WHERE `package_id`=%s
        """
        val = (name, destination, duration, price, description, sid, is_international, id)

    cursor.execute(sql, val)
    con.commit()
    return redirect('/admin/packagelist')
  
@app.route("/admin/deletepackage/<int:id>")
def deletepackage(id):
    sql = "DELETE FROM `tbl_package` WHERE package_id = %s"
    val = (id,)
    cursor.execute(sql,val)
    con.commit()
    return redirect('/admin/packagelist')  

@app.route('/get_subcategories/<int:catid>')
def get_subcategories(catid):
    try:
        cursor = con.cursor()
        sql = "SELECT subcategory_id, name FROM subcategory WHERE category_id = %s"
        cursor.execute(sql, (catid,))
        rows = cursor.fetchall()
        cursor.close()
        result = [{"id": row[0], "name": row[1]} for row in rows]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/admin/transport')
def transport():
    sql = "SELECT package_id, package_name, is_international FROM `tbl_package` ORDER BY package_id DESC"
    cursor.execute(sql)
    transport = cursor.fetchall()
    return render_template("admin/transport.html",transport = transport)

@app.route("/admin/addtransport", methods=['POST', 'GET'])
def addtransport():
    if request.method == 'POST':
        mode = request.form['mode']
        from_location = request.form['from_location']
        to_location = request.form['to_location']
        departure_time = request.form['departure_time']
        arrival_time = request.form['arrival_time']
        travel_date = request.form['travel_date']
        package_id = request.form['package_id']
        
        if not mode or not package_id:
            flash("Please fill in required fields")
            return redirect(url_for('transport'))

        sql = "INSERT INTO `travel`(`mode`, `from_location`, `to_location`, `departure_time`, `arrival_time`, `travel_date`,`package_id`) VALUES (%s,%s,%s,%s,%s,%s,%s)"
        val = (mode, from_location, to_location, departure_time, arrival_time, travel_date, package_id)
        cursor.execute(sql, val)
        con.commit()
        return redirect('/admin/transportlist')

@app.route('/admin/transportlist')
def transportlist():
    sql = "SELECT t.*,p.package_name FROM travel AS t JOIN tbl_package AS p ON t.package_id = p.package_id ORDER BY t.travel_id DESC"
    cursor.execute(sql,)
    transport = cursor.fetchall()
    print(transport)
    return render_template("admin/transportlist.html",trans = transport)

@app.route("/admin/updatetransport/<int:travel_id>", methods=['POST'])
def updatetransport(travel_id):
    mode = request.form['mode']
    from_location = request.form['from_location']
    to_location = request.form['to_location']
    departure_time = request.form['departure_time']
    arrival_time = request.form['arrival_time']
    travel_date = request.form['travel_date']
    package_id = request.form['package_id']

    if arrival_time == '':
        arrival_time = None  

    sql = """UPDATE travel SET 
                `mode` = %s,
                `from_location` = %s,
                `to_location` = %s,
                `departure_time` = %s,
                `arrival_time` = %s,
                `travel_date` = %s,
                `package_id` = %s
             WHERE `travel_id` = %s"""
    val = (mode, from_location, to_location, departure_time, arrival_time, travel_date, package_id, travel_id)
    cursor.execute(sql, val)
    con.commit()
    return redirect('/admin/transportlist')

@app.route("/admin/edittransport/<int:travel_id>", methods=['GET'])
def edittransport(travel_id):
    cursor.execute("SELECT * FROM travel WHERE travel_id = %s", (travel_id,))
    data = list(cursor.fetchone())

    if data[5]:
        try:
            data[5] = datetime.strptime(str(data[5]), "%H:%M:%S").strftime("%H:%M")
        except:
            data[5] = str(data[5])[:5]
    else:
        data[5] = ""

    if data[6]:
        try:
            data[6] = datetime.strptime(str(data[6]), "%H:%M:%S").strftime("%H:%M")
        except:
            data[6] = str(data[6])[:5]
    else:
        data[6] = ""

    if isinstance(data[7], (datetime, date)):
        data[7] = data[7].strftime('%Y-%m-%d')
    else:
        data[7] = str(data[7])[:10]

    cursor.execute("SELECT package_id, package_name FROM tbl_package")
    packages = cursor.fetchall()
    print("Data sent to template:", data)  
    return render_template("admin/transport_edit.html", data=data, packages=packages)

@app.route("/admin/deletetransport/<int:travel_id>")
def deletetransport(travel_id):
    sql = "DELETE FROM `travel` WHERE travel_id = %s"
    val = (travel_id,)
    cursor.execute(sql,val)
    con.commit()
    return redirect('/admin/transportlist')

@app.route('/admin/userlist')
def userlist():
    sql = "SELECT * FROM `user_reg` order by user_id DESC"
    cursor.execute(sql)
    user = cursor.fetchall()
    print(user)
    return render_template("admin/userlist.html",user = user)

@app.route('/userblock/<int:id>')
def userblock(id):
    id = id
    sql = "SELECT * FROM `user_reg` WHERE user_id = %s"
    val = (id,)
    cursor.execute(sql,val)
    data = cursor.fetchone()
    if data[7] == 0:
        sql = "UPDATE `user_reg` SET status = 1 WHERE user_id = %s"
    else:
        sql = "UPDATE `user_reg` SET status = 0 WHERE user_id = %s"  
    cursor.execute(sql,val)
    con.commit()
    return redirect (url_for('userlist'))

@app.route('/admin/bookinglist')
def bookinglist():
    sql = "SELECT b.*, p.package_name FROM booking AS b JOIN tbl_package AS p ON b.package_id = p.package_id ORDER BY b.booking_id DESC";
    cursor.execute(sql)
    booking = cursor.fetchall()
    return render_template("admin/booking.html", booking=booking)

@app.route('/admin/feedbacklist')
def feedbacklist():
    sql = "SELECT * FROM `feedback`"
    cursor.execute(sql)
    feedbacklist = cursor.fetchall()
    print(feedbacklist)
    return render_template("admin/feedbacklist.html",feedbacklist = feedbacklist)

#user section
@app.route('/')
def userdashboard():
    sql = "SELECT * FROM `category` order by category_id DESC LIMIT 4"
    cursor.execute(sql)
    category = cursor.fetchall()
    sql = "SELECT * FROM `tbl_package` order by package_id DESC LIMIT 6"
    cursor.execute(sql)
    package = cursor.fetchall()
    sql = "SELECT * FROM `feedback`"
    cursor.execute(sql)
    feedback = cursor.fetchall()
    return render_template("user/dashboard.html",cate = category,pack = package,feedback = feedback)

@app.route('/search', methods=['POST'])
def search():
    search_term = request.form['search'].strip().lower()
    cursor = con.cursor()
    cursor.execute("""
        SELECT p.*, s.name, s.location
        FROM tbl_package p
        JOIN subcategory s ON p.subcategory_id = s.subcategory_id
    """)
    all_packages = cursor.fetchall()
    matched_packages = []
    for pkg in all_packages:
        package_destination = pkg[2].lower()
        subcat_name = pkg[-2].lower()
        subcat_location = pkg[-1].lower()

        combined_text = f"{package_destination} {subcat_name} {subcat_location}"
        if difflib.get_close_matches(search_term, [package_destination, subcat_name, subcat_location], n=1, cutoff=0.6):
            matched_packages.append(pkg)
    return render_template('user/user_package.html', userpackage=matched_packages)

@app.route('/suggest', methods=['GET'])
def suggest():
    term = request.args.get('term', '').strip().lower()
    cursor = con.cursor()

    cursor.execute("SELECT DISTINCT name FROM subcategory")
    results = cursor.fetchall()

    suggestions = []
    for row in results:
        name = row[0]
        if term in name.lower():
            suggestions.append(name)

    return jsonify(suggestions)

@app.route('/categorypackages/<int:category_id>')
def view_packages_by_category(category_id):
    sql = """SELECT p.* FROM tbl_package p JOIN subcategory s ON p.subcategory_id = s.subcategory_id WHERE s.category_id = %s ORDER BY p.package_id DESC"""
    cursor.execute(sql,(category_id,))
    package = cursor.fetchall()
    return render_template("user/user_package.html",userpackage = package)

@app.route('/user/user_category')
def user_category(): 
    return render_template("user/user_category.html")  

@app.route('/usercategory')
def usercategory():
    sql = "SELECT * FROM `category`"
    cursor.execute(sql)
    usercategory = cursor.fetchall()
    return render_template("user/user_category.html",usercategory = usercategory)

@app.route('/usersubcategory/<int:id>')
def usersubcategory(id):
    #domestic subcategories
    sql_domestic = "SELECT * FROM `subcategory` WHERE category_id = %s AND is_international = 0"
    cursor.execute(sql_domestic,(id,))
    domestic = cursor.fetchall()

    #international subcategories
    sql_international = "SELECT * FROM `subcategory` WHERE category_id = %s AND is_international = 1"
    cursor.execute(sql_international,(id,))
    international = cursor.fetchall()
    return render_template("user/user_subcategory.html",domestic=domestic, international=international)

@app.route('/userpackage/<int:id>')
def userpackage(id):
    sql = "SELECT * FROM `tbl_package` WHERE subcategory_id = %s"
    val = (id,)
    cursor.execute(sql,val)
    userpackage = cursor.fetchall()
    print(userpackage)
    return render_template("user/user_package.html",userpackage = userpackage)

@app.route('/upackage')
def upackage():
    sql = "SELECT * FROM `tbl_package`"
    cursor.execute(sql)
    upackage = cursor.fetchall()
    return render_template("user/user_package.html",userpackage = upackage)

@app.route('/packagedetails/<int:id>')
def packagedetails(id):
    sql = "SELECT * FROM tbl_package WHERE package_id = %s"
    cursor.execute(sql, (id,))
    packagedetails = cursor.fetchone()

    if not packagedetails:
        flash("Package Not Found")
        return redirect(url_for('userdashboard'))

    is_international = packagedetails[8]
    package_type = 'international' if is_international == 1 else 'domestic'

    if is_international == 1:
        sql_transport = """
            SELECT * FROM travel 
            WHERE package_id = %s AND mode = 'flight' AND travel_date >= CURDATE()
        """
    else:
        sql_transport = """
            SELECT * FROM travel 
            WHERE package_id = %s AND travel_date >= CURDATE()
        """

    cursor.execute(sql_transport, (id,))
    transport_modes = cursor.fetchall()
    travel_dates = [t[7] for t in transport_modes if t[7]]  

    converted_dates = []
    for d in travel_dates:
        if isinstance(d, str):
            converted_dates.append(datetime.strptime(d, "%Y-%m-%d").date())
        elif isinstance(d, datetime):
            converted_dates.append(d.date())
        else:
            converted_dates.append(d)

    travel_dates = sorted(set(converted_dates))  

    return render_template(
        'user/package_details.html',
        i=packagedetails,
        transport=transport_modes,
        package_type=package_type,
        travel_dates=travel_dates,
        package_id=id
    )

@app.route('/userbooking')
def userbooking():
    return render_template('userbooking.html')
  
@app.route('/user/registration',methods = ['POST','GET'])
def registration():
    if request.method == 'POST':
        name = request.form['uname']
        email = request.form['uemail']
        password = request.form['upassword']
        phone = request.form['uphone']
        address = request.form['address']
        hashed_password = generate_password_hash(password)
        cursor = con.cursor()
        sql = "SELECT * FROM `user_reg` WHERE email = %s"
        cursor.execute(sql,(email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Email already exist! please try logging in or use a different email","warning")
            return render_template('user/registration.html',redirect_to = url_for('registration'))
        sql = "INSERT INTO `user_reg` (`name`,`contact_no`,`email`,`password_hash`,`address`) VALUES(%s,%s,%s,%s,%s)"
        val = (name,phone,email,hashed_password,address)
        cursor.execute(sql,val)
        con.commit()
        flash('Registration successful! Please login.','success')
        return render_template("user/registration.html", redirect_to=url_for('login'))
    return render_template("user/registration.html")

@app.route('/user/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['uemail']
        password = request.form['upassword']

        sql = "SELECT * FROM `user_reg` WHERE email = %s"
        val = (email,)
        cursor.execute(sql, val)
        data = cursor.fetchone()

        if data:
            if check_password_hash(data[5], password):
                if data[7] == 1:  # Blocked
                    flash("Your account is blocked.", "danger")
                    return render_template("user/login.html")

                session['user_id'] = data[0]
                session['user_name'] = data[1]
                session['user_email'] = data[3]
                flash("Login Successful!", "success")
                return render_template("user/login.html", redirect_to=url_for('userdashboard'))
            else:
                flash("Invalid Credential","danger")
                return render_template('user/login.html')

        else:
            flash("Email not registered.","danger")
            return render_template('user/login.html')

    return render_template('user/login.html')            

                # Profile completeness check
'''incomplete_fields = [data[1], data[2], data[4], data[6], data[7], data[8], data[9], data[10]]
                if any(field in [None, '', ' '] for field in incomplete_fields):
                    flash("Please complete your profile first.", "info")
                    return render_template("user/login.html", redirect_to=url_for('editprofile'))
                else:
                    flash("Login Successful!", "success")
                    return render_template("user/login.html", redirect_to=url_for('userdashboard'))'''
            
@app.route('/logout')
def logout():
    session.pop('user_id',None)
    session.pop('user_name',None)
    session.pop('user_email',None)
    flash("You have been logged out.")
    return redirect(url_for('login'))

@app.route('/forgotpassword', methods = ['POST','GET'])
def forgotpassword():
    if request.method == 'POST':
        email = request.form['uemail']
        cursor.execute("SELECT * FROM `user_reg` WHERE email = %s",(email,))
        user = cursor.fetchone()

        if user:
            otp = str(random.randint(1000,9999))
            session['reset_email'] = email
            session['otp'] = otp

            msg = Message("Your OTP for password reset",sender="hetvisuthar311@gmail.com",recipients = [email])
            msg.body = f"Your OTP for password reset is : {otp}"
            mail.send(msg)
            flash("OTP has been sent to your email address.","success")
            return redirect(url_for('verifyotp'))
        else:
            flash("Email not found","danger")
    return render_template("user/forgotpassword.html")

@app.route('/verifyotp',methods = ['POST','GET'])
def verifyotp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        
        if entered_otp == session.get('otp'):
            return redirect(url_for('setnewpassword'))
        else:
            flash("Invalid OTP","danger")
            return redirect(url_for('verifyotp'))
    return render_template("user/verifyotp.html")

@app.route('/setnewpassword', methods = ['GET','POST'])
def setnewpassword():
    if request.method == 'POST':
        new_pass = request.form['newpass']
        confirm_pass = request.form['confirmpass']

        if new_pass != confirm_pass:
            flash("Password do not match","danger")
            return redirect(url_for('login'))
        
        hashed_pass = generate_password_hash(new_pass)
        email = session.get('reset_email')
        cursor.execute("UPDATE `user_reg` SET `password_hash` = %s WHERE email = %s",(hashed_pass,email))
        con.commit()
        flash("Password Updated Successfully","success")
        return redirect(url_for('login'))
    return render_template("user/setnewpassword.html")

@app.route('/user/profile')
def profile():
    if 'user_id' in session:
        user_id = session['user_id']
        cursor.execute("SELECT * FROM `user_reg` WHERE user_id = %s",(user_id,))
        user = cursor.fetchone()

        if user:
            return render_template("user/profile.html",user = user)
        else:
            flash("User not found.","danger")
            return redirect(url_for('login'))
    else:
        flash("Please login to access your profile.","warning") 
        return redirect(url_for('login'))  
     
@app.route('/user/editprofile', methods=['GET', 'POST'])
def editprofile():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor.execute("SELECT * FROM `user_reg` WHERE user_id = %s", (user_id,))
    current_user = cursor.fetchone()

    if not current_user:
        flash("User not found.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        dob = request.form['dob'].strip()
        gender = request.form['gender'].strip()
        address = request.form['address'].strip()
        city = request.form['city'].strip()
        pincode = request.form['pincode'].strip()
        country = request.form['country'].strip()

        if not all([name, phone, dob, gender, address, city, country, pincode]):
            flash("Please complete all required fields to proceed.", "warning")
            return render_template("user/editprofile.html", user=current_user)

        data_changed = (
            name != current_user[1] or
            phone != current_user[2] or
            dob != str(current_user[4]) or
            address != current_user[6] or
            gender != current_user[8] or
            city != current_user[9] or
            country != current_user[10] or
            pincode != current_user[11]
        )

        if data_changed:
            sql = """
                UPDATE `user_reg` SET
                `name`= %s, `contact_no`= %s, `date_of_birth`= %s, `address`= %s,
                `gender`= %s, `city`= %s, `country`= %s, `pincode`= %s
                WHERE `user_id` = %s
            """
            val = (name, phone, dob, address, gender, city, country, pincode, user_id)
            cursor.execute(sql, val)
            con.commit()
            flash("Profile updated successfully!", "success")
            redirect_to = url_for('userdashboard')
        else:
            flash("No changes detected.", "info")
            redirect_to = None
        cursor.execute("SELECT * FROM `user_reg` WHERE user_id = %s", (user_id,))
        updated_user = cursor.fetchone()
        return render_template("user/editprofile.html", user=updated_user, redirect_to=redirect_to)
    return render_template("user/editprofile.html", user=current_user)

@app.route('/user/bookinghistory')
def bookinghistory():
    if 'user_id' not in session:
        flash("Please login first", "danger")
        return redirect(url_for('login'))
    user_id = session['user_id']

    sql = """
        SELECT 
            b.booking_id, 
            p.package_name, 
            p.package_destination, 
            b.travel_date, 
            b.no_of_members, 
            b.mode, 
            b.status,
            (p.package_price * b.no_of_members) AS total_price
        FROM booking b
        JOIN tbl_package p ON b.package_id = p.package_id
        WHERE b.user_id = %s
        ORDER BY b.booking_id DESC
    """
    cursor.execute(sql, (user_id,))
    rows = cursor.fetchall()
    bookings = []
    for row in rows:
        bookings.append({
            'booking_id': row[0],
            'package_name': row[1],
            'package_destination': row[2],
            'travel_date': row[3],
            'no_of_members': row[4],
            'mode': row[5],
            'status': row[6],
            'total_price': row[7]
        })
    return render_template("user/bookinghistory.html", bookings=bookings)

@app.route('/user/cancelbooking',methods = ['POST'])
def cancelbooking():
    if 'user_id' not in session:
        flash("Please login first","danger")
        return redirect(url_for('login'))
    booking_id = request.form.get('booking_id')
    sql = "SELECT * FROM booking WHERE booking_id = %s AND user_id = %s"
    cursor.execute(sql,(booking_id,session['user_id']))
    booking = cursor.fetchone()

    if not booking:
        flash("Booking not found or unauthorized access","danger")
        return redirect(url_for('bookinghistory'))
    sql = "UPDATE booking SET status = 'cancelled' WHERE booking_id = %s AND user_id = %s "
    cursor.execute(sql,(booking_id,session['user_id']))
    con.commit()
    flash("Booking cancelled successfully","success")
    return redirect(url_for('bookinghistory'))

@app.route('/confirm_order1', methods=['GET', 'POST'])
def confirm_order1():
    try:
        if request.method == 'POST':
            cursor = con.cursor()

            user_id = session.get('user_id')
            package_id = request.form.get('package_id')
            fullname = request.form.get('fullname')
            email = request.form.get('email')
            phone_no = request.form.get('phone_no')
            mode = request.form.get('mode')
            travel_date = request.form.get('travel_date')
            no_of_members = request.form.get('no_of_members')  
            message = request.form.get('message')
            amount = request.form.get('amount')  

            query = """
                INSERT INTO booking
                (user_id, package_id, fullname, email, phone_no, mode, travel_date, no_of_members, message, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (user_id, package_id, fullname, email, phone_no, mode, travel_date, no_of_members, message, amount)
            cursor.execute(query, params)
            msg = Message(subject="Your Package Booking was Successful!",
                          sender="hetvisuthar311@gmail.com",
                          recipients=[email])
            msg.body = f"""Dear {fullname},

Thank you for booking your tour with us!

Your package has been successfully confirmed. Below are your booking details:
- Package ID: {package_id}
- Travel Date: {travel_date}
- No. of Members: {no_of_members}
- Amount Paid: {amount}
- Mode: {mode}

We look forward to providing you with a great experience!

Regards,
Tour Admin
"""
            mail.send(msg)
            con.commit()
            cursor.close()
            return redirect(url_for('/'))
        else:
            return "Payment confirmation page"

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create_razorpay_order',methods = ['POST'])
def create_razorpay_order():
    try:
        amount = int(float(request.form['amount'])* 100)
        order = razorpay_client.order.create({
            "amount" : amount,
            "currency" : "INR",
            "payment_capture" : 1
        })
        return jsonify({
            "status" : "success",
            "order_id" : order['id'],
            "amount" : order['amount']
        }) 
    except Exception as e:
        return jsonify({"status" : "error" , "message" : str(e)})

from flask import request, jsonify

@app.route('/admin/confirm_booking', methods=['POST'])
def confirm_booking():
    data = request.get_json()
    booking_id = data.get('booking_id')
    cursor = con.cursor()
    cursor.execute("UPDATE booking SET status = %s WHERE booking_id = %s", ('Confirmed', booking_id))
    con.commit()
    cursor.close()

    return jsonify({'status': 'success'})

@app.route('/user/feedback', methods=['POST', 'GET'])
def feedback():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        feedback_image = request.files.get('feedback_image')
        post = request.form.get('post', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not phone or not post or not message:
            flash("Please fill in all required fields.", "danger")
            return render_template("/user/feedback.html")

        feedbackimgpath = os.path.join('static', 'uploads', 'feedback')
        if not os.path.exists(feedbackimgpath):
            os.makedirs(feedbackimgpath)

        db_img_path = None
        if feedback_image and feedback_image.filename != '':
            filename = secure_filename(feedback_image.filename)
            imgpath = os.path.join(feedbackimgpath, filename)
            feedback_image.save(imgpath)
            db_img_path = os.path.join('uploads', 'feedback', filename)

        sql = "INSERT INTO `feedback`(`name`, `email`, `phone`, `message`, `image`, `post`) VALUES (%s, %s, %s, %s, %s, %s)"
        val = (name, email, phone, message, db_img_path, post)
        cursor.execute(sql, val)
        con.commit()

        flash("Feedback submitted successfully!", "success")
        return redirect(url_for('feedback'))

    return render_template("/user/feedback.html")

if __name__ == '__main__':
    app.run(debug=True) 
    