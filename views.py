from flask import render_template, request, session, redirect, url_for, flash, jsonify
from lxml import etree  
import lxml.etree as ET
import random, string
from hackergram import app
from bson.objectid import ObjectId
import requests as http_requests
import re
import json
import models as models
import os
import urllib.request
import subprocess
# To add CSRF protection, uncomment the following line and the csrf initialization below
# from flask_wtf.csrf import CSRFProtect, generate_csrf

# To enable CSRF protection, uncomment the following line
# csrf = CSRFProtect(app)

OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Change this later when in the GNS3 Lab

# Renders errors
def error(msg):
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
        return render_template('error.html', current_user=user, msg=msg)
    else:
        return render_template('error.html', msg=msg)


# Renders errors
@app.route('/reset', methods=['GET', 'POST'])
def reset():
    models.reset()
    flash('Hackergram was reset', 'success')
    return redirect(url_for('home'))


# Homepage (redirects to login if user is not logged in)
@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)        
   
        if user and username == 'admin':
            return redirect(url_for('admin_dashboard'))
        
        try:
            posts_to_show = models.get_posts('')[::-1]
        except Exception as e:
            return error(e)

        if user:
            return render_template('home.html', current_user=user, posts=posts_to_show)
    return redirect(url_for('login'))


# Signs in users
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
        flash('You are already logged in', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form['username']
    password = request.form['password']

    if username == "" or password == "":
        flash("Invalid username or password", 'error')
        return redirect(url_for('login'))

    try:
        user = models.login(username, password)
    except Exception as e:
        return error(e)

    if not user:
        flash('Invalid username or password', 'error')
        return redirect(url_for('login'))

    session['username'] = username
    flash('Signed in successfully', 'success')
    return redirect(url_for('home'))


# Signs up new users
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
        flash('You are already logged in', 'error')
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template('signup.html')

    username = request.form['username']
    name = request.form['name']
    password = request.form['password']

    if username == "" or name == "" or password == "":
        flash("Invalid username, name or password", 'error')
        return redirect(url_for('signup'))

    try:
        user = models.get_user_settings(username)
    except Exception as e:
        return error(e)

    if user:
        flash("@%s is already taken" % user.username, 'error')
        return redirect(url_for('signup'))

    try:
        user = models.signup(username, password, name)
    except Exception as e:
        return error(e)

    session['username'] = username
    flash('Account created', 'success')
    return redirect(url_for('home'))


# Logs out users
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))


# Allows a user to see and change their settings
@app.route('/settings', methods=["GET", "POST"])
def settings():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('settings.html', current_user=user)
    
    new_name = request.form['name']
    if not new_name:
        new_name = user.name

    new_bio = request.form['bio']
    if not new_bio:
        new_bio = user.bio

    new_photo = request.files['photo']
    new_photo = request.files.get('photo', None)
    if not new_photo:
        new_photo_filename = user.photo
    else:
        new_photo_filename = new_photo.filename  
        new_photo.save(os.path.join(app.config['photos_folder'], new_photo_filename))
    
    photo_url = request.form.get("photo_url")
    
    if photo_url and photo_url.strip() != '':
        try:
            url_filename = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)) + '_url_image.jpg' 
            filepath = os.path.join(app.config['photos_folder'], url_filename)
            urllib.request.urlretrieve(photo_url, filepath)
            new_photo_filename = url_filename
        except Exception as e:
            flash(f"Failed to download image from URL: {e}", 'error')

    current_password = request.form['currentpassword']
    new_password = request.form['newpassword']
    if not new_password:
        new_password = current_password
    else:
        if current_password == new_password:
            flash("New password must be different from current password", 'error')
            return render_template('settings.html', current_user=user)
    if current_password != user.password:
        flash("Invalid password", 'error')
        return render_template('settings.html', current_user=user)
    
    try:
        user = models.update_user_settings(username, new_name, new_password, new_bio, new_photo_filename)
    except Exception as e:
        return error(e)

    if user:
        flash("Your settings were updated", 'success')
        return render_template('settings.html', current_user=user)


# Shows the profile of user with [username]
@app.route('/profile', methods=["GET"])
def profile():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)

        u = request.args.get('username')
        if not u:
            return error("No user provided")
        try:
            profile = models.get_profile(u)
            if profile == None:
                return error("User does not exist")
        except Exception as e:
            return error(e)
        
        if user:
            is_friend = False
            is_pending_requestee = False
            is_pending_requester = False
            if u in models.get_username_of_friends(username):
                is_friend = True
            else:
                if models.is_request_pending(u, username):
                    is_pending_requestee = True
                if models.is_request_pending(username, u):
                    is_pending_requester = True
            return render_template('profile.html', current_user=user, profile=profile, is_friend=is_friend, is_pending_requester=is_pending_requester, is_pending_requestee=is_pending_requestee)
    return redirect(url_for('login'))


# Creates a new post
@app.route('/create_post', methods=["GET", "POST"])
def create_post():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))

    if request.method == 'GET':
        # Vulnerable version - no CSRF token
        return render_template('create_post.html', current_user=user)
        # To add CSRF protection, uncomment the import at the top of the file and uncomment this line:
        # return render_template('create_post.html', current_user=user, csrf_token=generate_csrf())

    # No CSRF verification in vulnerable version
    # With CSRF protection enabled, verification happens automatically for POST requests
    
    new_content = request.form['content']

    if not new_content:
        flash("You cannot publish an empty post", 'error')
        # Vulnerable version
        return render_template('create_post.html', current_user=user)
        # To add CSRF protection, uncomment the import at the top of the file and uncomment this line:
        # return render_template('create_post.html', current_user=user, csrf_token=generate_csrf())

    try:
        new_post = models.create_post(username, new_content)
    except Exception as e:
        return error(e)

    if new_post:
        flash("New post published", 'success')
    else:
        flash("Failed to publish the new post", 'error')

    return redirect(url_for('home'))

@app.route('/generate_post', methods=['POST'])
def generate_post():
    if 'username' in session:
        username = session['username']
    else:
        return redirect(url_for('login'))
    
    user_input = request.json.get("prompt") if request.is_json else request.form.get("prompt")
    if not user_input:
        return jsonify({"error": "Prompt is required"}), 400

    # URL detection regex pattern
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?::\d+)?(?:/[^\s]*)?'
    urls = re.findall(url_pattern, user_input)
    
    fetched_content = ''
    if urls:
        try:
            url = urls[0]
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
                
            # Validate URL before fetching
            if not url.startswith(('http://', 'https://')):
                raise ValueError("Invalid URL format")
                
            resp = http_requests.get(url, timeout=3, verify=False) 
            resp.raise_for_status()
            fetched_content = resp.text[:1000] 
            app.logger.info(f"Successfully fetched content from URL: {url}")
            
            # Remove the URL from user input and combine with fetched content
            user_input = re.sub(url_pattern, '', user_input).strip()
            full_prompt = f"Content from URL:\n{fetched_content}\n\nUser's additional input: {user_input}"
        except http_requests.exceptions.ConnectionError as e:
            app.logger.error(f"Connection error for URL {url}: {str(e)}")
            full_prompt = f"{user_input}\n\nNote: Could not connect to the URL. Please ensure the URL is correct and the server is running."
        except http_requests.exceptions.Timeout as e:
            app.logger.error(f"Timeout error for URL {url}: {str(e)}")
            full_prompt = f"{user_input}\n\nNote: The URL request timed out. Please try again later."
        except http_requests.exceptions.RequestException as e:
            app.logger.error(f"Request error for URL {url}: {str(e)}")
            full_prompt = f"{user_input}\n\nNote: Error accessing the URL: {str(e)}"
        except Exception as e:
            app.logger.error(f"Unexpected error fetching URL content: {str(e)}")
            full_prompt = f"{user_input}\n\nNote: An unexpected error occurred while fetching the URL content."
    else:
        full_prompt = f"Please create a social media post for this: {user_input}"

    payload = {
        "model": "mistral",
        "prompt": full_prompt,
        "stream": False
    }

    try:
        response = http_requests.post(url=OLLAMA_API_URL, json=payload)
        response_text = response.text

        try:
            response_json = response.json()
            generated_post = response_json.get("response", "")
            models.insert_chat_log(username, user_input, generated_post)
        except ValueError as json_error:
            app.logger.error(f"JSON parsing error: {str(json_error)}")
            match = re.search(r'"response"\s*:\s*"([^"]*)"', response_text)
            generated_post = match.group(1) if match else "Error: Could not parse response."

        if not generated_post:
            generated_post = "Error generating content."

    except Exception as e:
        app.logger.error(f"Error in generate_post: {str(e)}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"content": generated_post})


# Edits post with [id]
@app.route('/edit_post', methods=["GET", "POST"])
def edit_post():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))

    if request.method == 'GET':
        post_id = request.args.get('id')
        if int(post_id) not in models.get_post_ids(username):
            flash("You cannot edit other users' posts", 'error')
            return redirect(url_for('home'))
        try:
            post = models.get_post(post_id)
        except Exception as e:
            return error(e)
        return render_template('edit_post.html', current_user=user, post=post)

    new_content = request.form['content']
    post_id = request.form['id']

    if int(post_id) not in models.get_post_ids(username):
        flash("You cannot edit other users' posts", 'error')
        return redirect(url_for('home'))

    if not new_content:
        flash("You cannot publish an empty post", 'error')
        return render_template('edit_post.html', current_user=user, post=post)

    try:
        new_post = models.edit_post(post_id, new_content)
    except Exception as e:
        return error(e)

    if new_post:
        flash("Post was edited", 'success')
    else:
        flash("Failed to edit post", 'error')

    return redirect(url_for('home'))


# Deletes post with [id]
@app.route('/delete_post', methods=["GET"])
def delete_post():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))
    if request.method == 'GET':
        post_id = request.args.get('id')
        if int(post_id) not in models.get_post_ids(username):
            flash("You cannot delete other users' posts", 'error')
            return redirect(url_for('home'))
        try:
            post = models.delete_post(post_id)
        except Exception as e:
            return error(e)
        flash("Post deleted", 'success')
        return redirect(url_for('home'))


# Sends friendship request to user with [username]
@app.route('/request_friend', methods=["POST"])
def request_friend():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))

    new_friend = request.form['username']
    if not models.get_user_settings(new_friend):
        flash("@%s does not exist" % new_friend, 'error')
        return redirect(url_for('home'))
    if not new_friend or new_friend == username:
        flash("Invalid username", 'error')
        return redirect(url_for('home'))
    if new_friend in models.get_username_of_friends(username): 
        flash("@%s is already your friend" % new_friend, 'error')
        return redirect(url_for('home'))
    if models.is_request_pending(new_friend, username):
        flash("You have a pending friendship request to/from @%s." % new_friend, 'error')
        return redirect(url_for('home'))

    try:
        new_request = models.new_friend_request(username, new_friend)
    except Exception as e:
        return error(e)

    if new_request:
        flash("Friendship request sent to @%s" % new_friend, 'success')
    else:
        flash("Failed to send friendship request to @%s" % new_friend, 'error')

    return redirect(url_for('profile')+'?username='+new_friend)


# Accepts friendship request from user with [username]
@app.route('/requests', methods=["GET"])
def requests():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))
    try:
        friend_requests = models.get_friend_requests(username)
    except Exception as e:
        return error(e)

    accept_friend = request.args.get('username', default = "")
    if accept_friend == "":
        return render_template('requests.html', current_user=user, friend_requests=friend_requests)
    if not accept_friend or not models.is_request_pending(accept_friend, username):
        flash("Invalid friendship request", 'error')
        return render_template('requests.html', current_user=user, friend_requests=friend_requests)
    try:
        new_friend = models.accept_friend_request(username, accept_friend)
    except Exception as e:
        return error(e)
    if new_friend:
        flash("Friendship request from @%s was accepted" % accept_friend, 'success')
    else:
        flash("Failed to accept friendship request from @%s" % accept_friend, 'error')

    origin = request.args.get('origin', default = "")
    if origin == 'requests':
        return redirect(url_for('requests'))
    elif origin == 'profile':
        return redirect(url_for('profile')+'?username='+accept_friend)
    else:
        return redirect(url_for('home'))


# Removes friendship request from user with [username]
@app.route('/remove_request', methods=["POST"])
def remove_request():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))
    
    tentative_friend = request.form['username']
    if not tentative_friend:# or not models.is_request_pending(tentative_friend, username) or not models.is_request_pending(username, tentative_friend):
        return error("Invalid friendship request")
    try:
        success = models.remove_friend_request(username, tentative_friend)
    except Exception as e:
        return error(e)
    if success:
        flash("Friendship request was removed", 'success')
    else:
        flash("Failed to remove friendship request", 'error')
    
    origin = request.form['origin']
    if origin == 'requests':
        return redirect(url_for('requests'))
    elif origin == 'profile':
        return redirect(url_for('profile')+'?username='+tentative_friend)
    else:
        return redirect(url_for('home'))
    

# Removes friendship with user with [username]
@app.route('/remove_friend', methods=["POST"])
def remove_friend():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))
    
    friend = request.form['username']
    if not friend or friend not in models.get_username_of_friends(username):
        return error("Introduce an existing friend.")
    try:
        success = models.remove_friend(username, friend)
    except Exception as e:
        return error(e)
    if success:
        flash("@%s is no longer your friend" % friend, 'success')
    else:
        flash("Failed to remove friend", 'error')
    
    return redirect(url_for('profile')+'?username='+friend)


# Shows friends of user with [username] that match the search [query]
@app.route('/friends', methods=["GET"])
def friends():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))

    u = request.args.get('username')
    if not u:
        return error("No user provided")
    query = request.args.get('search', default = "")

    try:
        friends = models.get_friends(u, query)
    except Exception as e:
        return error(e)

    return render_template('friends.html', current_user=user, friends=friends, username=u, query=query)


# Shows users that match the search [query]
@app.route('/users', methods=["GET"])
def users():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))

    query = request.args.get('search', default = "")

    try:
        users = models.get_users(query)
    except Exception as e:
        return error(e)

    return render_template('users.html', current_user=user, users=users, query=query)


@app.route('/posts', methods=["GET", "POST"])
def posts():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)
    else:
        return redirect(url_for('login'))

    query = ""

    if request.method == "POST":
        try:
            parser = ET.XMLParser(
                resolve_entities=True,
                load_dtd=True,
                no_network=False,
                huge_tree=True
            )

            if request.content_type == "application/xml":
                xml_data = request.data.decode("utf-8")  # Get raw XML input
            else:
                search_term = request.form.get('search', '')
                xml_data = f'<?xml version="1.0"?><root><query>{search_term}</query></root>'  # Convert input to XML

            root = ET.fromstring(xml_data, parser=parser)
            query = root.findtext("query")

        except Exception as e:
            return error(e)

    else:
        query = request.args.get('search', '')

    try:
        posts = models.get_posts(query)[::-1]
    except Exception as e:
        return error(e)

    return render_template('posts.html', current_user=user, posts=posts, query=query)

@app.route("/chatlog")
def chatlog():
    if 'username' in session:
        username = session['username']
        user = models.get_user_settings(username)

        search = request.args.get('search', '').strip()
        lower_search = search.lower() #Case insensitive
        if search:
            query = {
                "$where": "function() { return (this.user === '" + username + "' && this.prompt && this.prompt.toLowerCase().includes('" + lower_search + "')); }"
            }
        else:
            query = {"user": username}

        try:
            logs = models.get_chat_history(query)
        except Exception as e:
            return error(e)
        
        return render_template("chatlog.html", current_user=user, chatlogs=logs)
    else:
        return redirect(url_for('login'))

    
@app.route("/delete_chat", methods=["POST"]) 
def delete_chat():
    if 'username' not in session: 
        return redirect(url_for('login'))

    username = session['username']
    user = {"user": username}
    chat_id = request.form.get("chat_id")

    try:
        chat_object_id = ObjectId(chat_id)
    except Exception as e:
        flash("Invalid chat id.")
        return redirect(url_for('chatlog'))
        
    print(f"I am deleting the post with chat id {chat_object_id} for user {session['username']}")
    result = models.mongo.db.chat_history.delete_one({"_id": chat_object_id, "user": session['username']})

    if result.deleted_count:
        flash("Chat log deleted successfully.")
    else:
        flash("Unable to delete chat log or it does not belong to you.")

    return redirect(url_for("chatlog"))

@app.route("/direct_messages", methods=["GET", "POST"])
def direct_messages():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user = models.get_user_settings(username)
    if request.method == "POST":
        recipient = request.form.get("username")
        message = request.form.get("message")

        if recipient and message:
            models.insert_dm(username, recipient, message)
            return redirect(url_for('direct_messages', username=recipient))
    else:
        recipient = request.args.get("username")

    if not recipient:
        return render_template("friends.html", current_user=user)

    messages = models.get_dm_conversation(username, recipient)
    recipient_profile = models.get_profile(recipient)
    return render_template("direct_messages.html", current_user=user, recipient=recipient, recipient_photo=recipient_profile.photo, messages=messages)

@app.route('/messages', methods=['GET'])
def messages():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user = models.get_user_settings(username)
    search = request.args.get('search', '').strip()

    try:
        query = json.loads(search)
    except Exception:
        query = {
            "$or": [
                {"sender": username},
                {"recipient": username}
            ]
        }
        if search:
            query["message"] = { "$regex": search, "$options": "i" }

    messages = list(models.mongo.db.direct_messages.find(query).sort("timestamp", -1))
    for msg in messages:
        msg["_id"] = str(msg["_id"])

    return render_template("messages.html", current_user=user, messages=messages, search=search)


# Admin access control decorator-like function
def admin_required():
    if 'username' not in session or session['username'] != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('home'))
    return None


# Admin Dashboard
@app.route('/admin', methods=['GET'])
def admin_dashboard():
    user = models.get_user_settings("admin")

    # Get statistics
    try:
        all_users = models.get_users('')
        all_posts = models.get_posts('')
        user_count = len(all_users)
        post_count = len(all_posts)
    except Exception as e:
        return error(str(e))
    
    return render_template('admin.html', current_user=user, user_count=user_count, post_count=post_count)


# Admin User Management
@app.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
    admin_check = admin_required()
    if admin_check:
        return admin_check
    
    username = session['username']
    user = models.get_user_settings(username)
    
    if request.method == 'GET':
        search = request.args.get('search', '')
        try:
            users = models.get_users(search)
        except Exception as e:
            return error(str(e))
        return render_template('admin.html', current_user=user, users=users, search=search, active_tab='users')
    
    # POST request - Add new user
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_name = request.form.get('name')
        new_password = request.form.get('password')
        
        if not new_username or not new_name or not new_password:
            flash('All fields are required', 'error')
            return redirect(url_for('admin_users'))
        
        # Check if user already exists
        try:
            existing_user = models.get_user_settings(new_username)
            if existing_user:
                flash(f'User @{new_username} already exists', 'error')
                return redirect(url_for('admin_users'))
            
            # Create new user
            models.signup(new_username, new_password, new_name)
            flash(f'User @{new_username} created successfully', 'success')
        except Exception as e:
            return error(str(e))
        
        return redirect(url_for('admin_users'))


# Admin Delete User
@app.route('/admin/users/delete', methods=['POST'])
def admin_delete_user():
    admin_check = admin_required()
    if admin_check:
        return admin_check
    
    user_to_delete = request.form.get('username')
    if not user_to_delete:
        flash('No username provided', 'error')
        return redirect(url_for('admin_users'))
    
    if user_to_delete == 'admin':
        flash('Cannot delete admin user', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        # Delete user's posts first
        user_posts = models.get_post_ids(user_to_delete)
        for post_id in user_posts:
            models.delete_post(post_id)
        
        # Delete user
        query = "DELETE FROM Users WHERE username = '%s'" % user_to_delete
        models.commit_to_database(query)
        flash(f'User @{user_to_delete} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))


# Admin Post Management
@app.route('/admin/posts', methods=['GET'])
def admin_posts():
    admin_check = admin_required()
    if admin_check:
        return admin_check
    
    username = session['username']
    user = models.get_user_settings(username)
    search = request.args.get('search', '')
    
    try:
        posts = models.get_posts(search)[::-1]  # Reverse to show newest first
    except Exception as e:
        return error(str(e))
    
    return render_template('admin.html', current_user=user, posts=posts, search=search, active_tab='posts')


# Admin Delete Post
@app.route('/admin/posts/delete', methods=['POST'])
def admin_delete_post():
    admin_check = admin_required()
    if admin_check:
        return admin_check
    
    post_id = request.form.get('post_id')
    if not post_id:
        flash('No post ID provided', 'error')
        return redirect(url_for('admin_posts'))
    
    try:
        models.delete_post(post_id)
        flash('Post deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting post: {str(e)}', 'error')
    
    return redirect(url_for('admin_posts'))


# Admin Statistics
@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    admin_check = admin_required()
    if admin_check:
        return admin_check
    
    username = session['username']
    user = models.get_user_settings(username)
    
    try:
        all_users = models.get_users('')
        all_posts = models.get_posts('')
        user_count = len(all_users)
        post_count = len(all_posts)
        
        # Additional statistics
        query = "SELECT COUNT(*) FROM Friends"
        friend_data = models.get_from_database(query)
        friend_count = friend_data[0][0] if friend_data else 0
        
        query = "SELECT COUNT(*) FROM Requests"
        request_data = models.get_from_database(query)
        request_count = request_data[0][0] if request_data else 0
        
    except Exception as e:
        return error(str(e))
    
    stats = {
        'users': user_count,
        'posts': post_count,
        'friendships': friend_count,
        'pending_requests': request_count
    }
    
    return render_template('admin.html', current_user=user, stats=stats, active_tab='stats')


def looks_like_sql(user_input: str) -> bool:
    sql_pattern = r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\s+.+"
    return bool(re.match(sql_pattern, user_input.strip(), re.IGNORECASE))

def is_dangerous_sql(sql: str) -> bool:
    lowered = sql.lower()
    return any(danger in lowered for danger in ["drop", "delete", "truncate"])

def generate_sql_prompt(natural_language_prompt):
    return f"""
You are an expert in converting English questions into SQL queries.

The database has these tables:
- Users(username, password, name, bio, photo)
- Posts(id, author, content, posted_at)
- Friends(id, username1, username2)
- Requests(id, username1, username2)
- LeaderboardEntry(username, name, photo, post_count, friend_count, total_score)

Query patterns:
1. For simple counts or lists:
   - Count posts: SELECT COUNT(*) FROM Posts
   - Count users: SELECT COUNT(*) FROM Users

2. For leaderboard queries:
   - Get top 10: SELECT * FROM LeaderboardEntry ORDER BY total_score DESC LIMIT 10
   - Get specific rank: SELECT * FROM LeaderboardEntry ORDER BY total_score 
   - Get user's rank: SELECT COUNT(*) + 1 FROM LeaderboardEntry WHERE total_score > (SELECT total_score FROM LeaderboardEntry WHERE username = 'username')

ONLY return SQL. No explanations, no markdown.
Q: {natural_language_prompt}
A:"""

def extract_sql_from_output(output: str) -> str:
    output = re.sub(r"^```sql\\s*", "", output, flags=re.IGNORECASE).strip()
    output = re.sub(r"```$", "", output).strip()
    match = re.search(r"(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)[\\s\\S]+?;", output, re.IGNORECASE)
    return match.group(0).strip() if match else output.strip()

def query_llm(prompt: str, model="llama2", temperature=0.1, seed=42):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "seed": seed
        }
    }
    
    try:
        response = http_requests.post(url=OLLAMA_API_URL, json=payload)
        if response.status_code != 200:
            print("LLM ERROR:", response.text)
            return "LLM Error: Request failed"
            
        response_json = response.json()
        raw_output = response_json.get("response", "").strip()
        sql = extract_sql_from_output(raw_output)
        return sanitize_sql(sql)
    except Exception as e:
        print("LLM ERROR:", str(e))
        return "LLM Error: Request failed"

def sanitize_sql(sql_query: str):
    return sql_query.strip()

def should_generate_sql(user_message):
    message = user_message.lower()
    sql_keywords = ["how many", "count", "total", "change", "show", "select", "items", "users", "prices", "sum", "average", "list", "update", "modify", "top", "leaderboard"]
    return any(keyword in message for keyword in sql_keywords)

def result_to_nl(user_message, sql_query, rows):
    if not rows:
        return "No results found."
    if "count" in sql_query.lower():
        return f"There are {rows[0][0]} results."
    return f"Here are the results:\n{rows}"

@app.route('/leaderboard', methods=['GET', 'POST'])
def leaderboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = models.get_user_settings(session['username'])
    display_response = None
    leaderboard = models.get_leaderboard_data()

    if request.method == 'POST':
        prompt = request.form.get('prompt', '').strip()
        if prompt and should_generate_sql(prompt):
            sql_prompt = generate_sql_prompt(prompt)
            sql_query = query_llm(sql_prompt)
            if is_dangerous_sql(sql_query):
                display_response = "❌ Destructive SQL commands (like DELETE or DROP) are not allowed."
            else:
                print(f"[+] SQL Query: {sql_query}")
                try:
                    if sql_query.lower().startswith("select"):
                        rows = models.get_from_database(sql_query)
                        display_response = result_to_nl(prompt, sql_query, rows) + f"\n(SQL Executed: {sql_query})"
                    else:
                        models.commit_to_database(sql_query)
                        display_response = f"✅ Query executed successfully.\n(SQL Executed: {sql_query})"
                except Exception as e:
                    display_response = f"❌ Failed to execute query: {e}"
        else:
            display_response = "No SQL generated for this prompt."

    return render_template('leaderboard.html', current_user=user, response=display_response, leaderboard=leaderboard)

# LLM-integrated content summarizer  
@app.route('/ai_summarize', methods=['GET', 'POST'])
def ai_summarize():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user = models.get_user_settings(username)
    
    # Handle GET request with post_id (from home page buttons)
    if request.method == 'GET':
        post_id = request.args.get('post_id', '').strip()
        if post_id:
            try:
                post = models.get_post(post_id)
                if post:
                    # Get the user information for the post author
                    user_info = models.get_user_settings(post.author)
                    if user_info:
                        # Create a post object with user info
                        post.name = user_info.name if user_info.name else post.author
                        post.photo = user_info.photo if user_info.photo else 'default.jpg'
                    else:
                        post.name = post.author
                        post.photo = 'default.jpg'
                    
                    content = post.content
                    summary_type = 'brief'  # Default for post summaries
                    
                    # Create prompt for LLM to summarize with HTML formatting
                    llm_prompt = f"""
Create a {summary_type} summary of the following social media post content.
Format your response using HTML for better presentation - use tags like <h3>, <p>, <ul>, <li>, <strong>, <em> etc.
Make it visually appealing for web display.

Post content: {content}

Provide your HTML-formatted summary:"""

                    payload = {
                        "model": "mistral", 
                        "prompt": llm_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.4,
                            "seed": 123
                        }
                    }

                    try:
                        response = http_requests.post(url=OLLAMA_API_URL, json=payload)
                        if response.status_code == 200:
                            response_json = response.json()
                            summary_html = response_json.get("response", "").strip()
                            
                            # VULNERABILITY: LLM output rendered directly without sanitization
                            # Attacker can prompt the LLM to generate malicious HTML/JS
                            from markupsafe import Markup
                            display_response = Markup(summary_html)
                            
                            # Log the interaction
                            models.insert_chat_log(username, content, summary_html)
                            
                            # Render template with both post and summary
                            return render_template('ai_summarize.html', current_user=user, 
                                                 summary_output=display_response, original_content=content,
                                                 post=post)
                        else:
                            flash("AI service unavailable", 'error')
                            return redirect(url_for('home'))
                    except Exception as e:
                        flash(f"Error generating summary: {str(e)}", 'error')
                        return redirect(url_for('home'))
                else:
                    flash("Post not found", 'error')
                    return redirect(url_for('home'))
            except Exception as e:
                flash(f"Error retrieving post: {str(e)}", 'error')
                return redirect(url_for('home'))
        else:
            # Regular GET request without post_id - show the form
            return render_template('ai_summarize.html', current_user=user)
    
    if request.method == 'POST':
        # Handle direct content input from the form
        content = request.form.get('content', '').strip()
        summary_type = request.form.get('type', 'brief')
        
        if content:
            # Create prompt for LLM to summarize with HTML formatting
            llm_prompt = f"""
Create a {summary_type} summary of the following social media post content.
Format your response using HTML for better presentation - use tags like <h3>, <p>, <ul>, <li>, <strong>, <em> etc.
Make it visually appealing for web display.

Post content: {content}

Provide your HTML-formatted summary:"""

            payload = {
                "model": "mistral", 
                "prompt": llm_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.4,
                    "seed": 123
                }
            }

            try:
                response = http_requests.post(url=OLLAMA_API_URL, json=payload)
                if response.status_code == 200:
                    response_json = response.json()
                    summary_html = response_json.get("response", "").strip()
                    
                    # VULNERABILITY: LLM output rendered directly without sanitization
                    # Attacker can prompt the LLM to generate malicious HTML/JS
                    from markupsafe import Markup
                    display_response = Markup(summary_html)
                    
                    # Log the interaction
                    models.insert_chat_log(username, content, summary_html)
                    
                    # Render template with summary
                    return render_template('ai_summarize.html', current_user=user, 
                                         summary_output=display_response, original_content=content)
                else:
                    flash("AI service unavailable", 'error')
            except Exception as e:
                flash(f"Error: {str(e)}", 'error')
        else:
            flash("Please provide content to summarize.", 'error')
    
    return render_template('ai_summarize.html', current_user=user)