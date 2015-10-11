import utilities
import time
from datetime import date
"""
    @ToDo: Loads of cleanup :D
"""

# ----------------------------------------------------------------------------
def index():
    """
        The main controller which redirects depending
        on the login status of the user and does some
        extra pre-processing
    """

    # If the user is logged in
    if session["auth"]:
        session["handle"] = session["auth"]["user"]["stopstalk_handle"]
        session["user_id"] = session["auth"]["user"]["id"]
        session.flash = "Logged in successfully"
        session.url_count = 0
        session.has_updated = "Incomplete"
        redirect(URL("default", "submissions", args=[1]))

    # Detect a registration has taken place
    # This will be the case when submission on
    # a register user form is done.
    row = db(db.auth_event.id > 0).select().last()
    if row:
        desc = row.description
    else:
        desc = ""

    # If the last auth_event record contains registered
    # or verification then retrieve submissions
    if desc.__contains__("Registered") or \
       desc.__contains__("Verification"):
        reg_user = desc.split(" ")[1]
        r = db(db.friends.user_id == reg_user).select()
        result = utilities.retrieve_submissions(int(reg_user))
        if result == "FAILURE":
            response.flash = "Some error occured"
        else:
            response.flash = "Successfully added " + \
                             str(result) + \
                             " submissions"

        row = db(db.auth_user.id == reg_user).select().first()
        tup = get_max_streak(row.stopstalk_handle)
        total_submissions = tup[1]
        total_days = tup[3]

        today = datetime.today().date()
        start = datetime.strptime(current.INITIAL_DATE,
                                  "%Y-%m-%d %H:%M:%S").date()

        per_day = total_submissions * 1.0 / (today - start).days
        db(db.auth_user.stopstalk_handle == row.stopstalk_handle).update(per_day=per_day)

        # User has a `set` of friends' ids
        # If user does not exists then initialize it with empty set
        if len(r) == 0:
            db.friends.insert(user_id=int(reg_user),
                              friends_list=str(set([])))

    response.flash = T("Please Login")
    return dict()

# ----------------------------------------------------------------------------
def get_max_streak(handle):
    """
        Get the maximum of all streaks
    """

    # Build the complex SQL query
    sql_query = """
                    SELECT time_stamp, COUNT(*)
                    FROM submission
                    WHERE submission.stopstalk_handle=
                """

    sql_query += "'" + handle + "' "
    sql_query += """
                    GROUP BY DATE(submission.time_stamp), submission.status;
                 """

    row = db.executesql(sql_query)
    streak = 0
    max_streak = 0
    prev = curr = start = None
    total_submissions = 0

    for i in row:

        total_submissions += i[1]
        if prev is None and streak == 0:
            prev = time.strptime(str(i[0]), "%Y-%m-%d %H:%M:%S")
            prev = date(prev.tm_year, prev.tm_mon, prev.tm_mday)
            streak = 1
            start = prev
        else:
            curr = time.strptime(str(i[0]), "%Y-%m-%d %H:%M:%S")
            curr = date(curr.tm_year, curr.tm_mon, curr.tm_mday)

            if (curr - prev).days == 1:
                streak += 1
            elif curr != prev:
                streak = 1

            prev = curr

        if streak > max_streak:
            max_streak = streak

    today = datetime.today().date()

    # There are no submissions in the database for this user
    if prev is None:
        return (0, 0, 0, 0)

    # Check if the last streak is continued till today
    if (today - prev).days > 1:
        streak = 0

    return max_streak, total_submissions, streak, len(row)

# ----------------------------------------------------------------------------
@auth.requires_login()
def notifications():
    """
        Check if any of the friends(includes CUSTOM) of
        the logged-in user is on a streak
    """

    if session["user_id"] is None:
        redirect(URL("default", "index"))

    ftable = db.friends
    atable = db.auth_user
    ctable = db.custom_friend

    # Check for streak of friends on stopstalk
    query = (ftable.user_id == session["user_id"])
    row = db(query).select(ftable.friends_list).first()

    # Will contain list of handles of all the friends along
    # with the Custom Users added by the logged-in user
    handles = []

    for user in eval(row.friends_list):
        query = (atable.id == user)
        user_data = db(query).select(atable.first_name,
                                     atable.last_name,
                                     atable.stopstalk_handle).first()

        handles.append((user_data.stopstalk_handle,
                        user_data.first_name + " " + user_data.last_name))

    # Check for streak of custom friends
    query = (ctable.user_id == session["user_id"])
    rows = db(query).select(ctable.first_name,
                            ctable.last_name,
                            ctable.stopstalk_handle)
    for user in rows:
        handles.append((user.stopstalk_handle,
                        user.first_name + " " + user.last_name))

    # List of users with non-zero streak
    users_on_streak = []

    for handle in handles:
        max_streak, total_submissions, curr_streak, total_days = get_max_streak(handle[0])

        # If streak is non-zero append to users_on_streak list
        if curr_streak:
            users_on_streak.append((handle, curr_streak))

    # Sort the users on streak by their streak
    users_on_streak.sort(key=lambda k: k[1], reverse=True)

    # The table containing users on streak
    table = TABLE(TR(TH(H3(STRONG("User"))),
                     TH(H3(STRONG("Streak"),
                        _class="center"))),
                  _class="table")

    # Append all the users to the final table
    for users in users_on_streak:
        handle = users[0]
        curr_streak = users[1]
        tr = TR(TD(H3(A(handle[1],
                        _href=URL("user", "profile", args=[handle[0]])))),
                TD(H3(str(curr_streak) + " ",
                      I(_class="fa fa-bolt",
                        _style="color:red"),
                      _class="center",
                      )))
        table.append(tr)

    return dict(table=table)

# ----------------------------------------------------------------------------
def compute_row(user, custom=False):
    """
        Computes rating and retrieves other
        information of the specified user
    """
    max_streak, total_submissions, curr_streak, total_days = get_max_streak(user.stopstalk_handle)

    if total_submissions == 0:
        return ()

    stable = db.submission

    # Find the total solved problems(Lesser than total accepted)
    query = (stable.stopstalk_handle == user.stopstalk_handle)
    query &= (stable.status == "AC")
    accepted = db(query).select(stable.problem_name, distinct=True)
    accepted = len(accepted)
    today = datetime.today().date()
    start = datetime.strptime(current.INITIAL_DATE,
                              "%Y-%m-%d %H:%M:%S").date()
    if custom:
        table = db.custom_friend
    else:
        table = db.auth_user

    query = (table.stopstalk_handle == user.stopstalk_handle)
    record = db(query).select().first()
    if record.per_day is None or \
       record.per_day == 0.0:
        per_day = total_submissions * 1.0 / (today - start).days
        db(query).update(per_day=per_day)

    else:
        row = db(query).select(table.per_day).first()
        per_day = row["per_day"]

    curr_per_day = total_submissions * 1.0 / (today - start).days
    diff = "%0.5f" % (curr_per_day - per_day)
    diff = float(diff)

    # This is not crazy. This is to solve the problem
    # if diff is -0.0
    if diff == 0.0:
        diff = 0.0

    # Unique rating formula
    # @ToDo: Improvement is always better
    rating = max_streak * 10 + \
             accepted * 50 + \
             (accepted * 100.0 / total_submissions) * 80 + \
             (total_submissions - accepted) * 15
    rating = int(rating)

    table = db.auth_user
    if custom:
        table = db.custom_friend

    # Update the rating whenever leaderboard page is loaded
    db(table.stopstalk_handle == user.stopstalk_handle).update(rating=rating)

    return (user.first_name + " " + user.last_name,
            user.stopstalk_handle,
            user.institute,
            rating,
            diff)

# ----------------------------------------------------------------------------
def leaderboard():
    """
        Get a table with users sorted by rating
    """

    reg_users = db(db.auth_user.id > 0).select()
    custom_users = db(db.custom_friend.id > 0).select()

    users = []

    for user in reg_users:
        tup = compute_row(user)
        if tup is not ():
            users.append(tup)

    for user in custom_users:
        tup = compute_row(user, True)
        if tup is not ():
            users.append(tup)

    # Sort users according to the rating
    users = sorted(users, key=lambda x: x[3], reverse=True)

    table = TABLE(_class="table")
    table.append(TR(TH("Name"),
                    TH("StopStalk Handle"),
                    TH("Institute"),
                    TH("StopStalk Rating"),
                    TH("Per Day Changes")))

    for i in users:

        # If there are no submissions of the user in the database
        if i is ():
            continue

        tr = TR()
        tr.append(TD(i[0]))
        tr.append(TD(A(i[1],
                     _href=URL("user", "profile", args=[i[1]]))))
        tr.append(TD(i[2]))
        tr.append(TD(i[3]))

        diff = "{:1.5f}".format(i[4])

        if float(diff) == 0.0:
            tr.append(TD("+" + diff, " ", I(_class="fa fa-minus")))
        elif i[4] > 0:
            tr.append(TD("+" + str(diff), " ", I(_class="fa fa-chevron-circle-up",
                                      _style="color: #0f0;")))
        elif i[4] < 0:
            tr.append(TD(diff, " ", I(_class="fa fa-chevron-circle-down",
                                      _style="color: #f00;")))

        table.append(tr)

    return dict(table=table)

# ----------------------------------------------------------------------------
def user():
    """
        Use the standard auth for user
    """
    return dict(form=auth())

# ----------------------------------------------------------------------------
@auth.requires_login()
def search():
    return dict()

# ----------------------------------------------------------------------------
@auth.requires_login()
def mark_friend():
    """
        Send a friend request
    """

    if len(request.args) < 1:
        session.flash = "Friend Request sent"
        redirect(URL("default", "search"))

    # Insert a tuple of users' id into the friend_requests table
    db.friend_requests.insert(from_h=session.user_id, to_h=request.args[0])
    session.flash = "Friend Request sent"
    redirect(URL("default", "search.html"))
    return dict()

# ----------------------------------------------------------------------------
@auth.requires_login()
def retrieve_users():
    """
        Show the list of registered users
    """

    atable = db.auth_user
    frtable = db.friend_requests
    q = request.get_vars.get("q", None)

    query = (atable.first_name.like("%" + q + "%",
                                    case_sensitive=False))
    query |= (atable.last_name.like("%" + q + "%",
                                    case_sensitive=False))
    query |= (atable.stopstalk_handle.like("%" + q + "%",
                                           case_sensitive=False))

    for site in current.SITES:
        field_name = site.lower() + "_handle"
        query |= (atable[field_name].like("%" + q + "%",
                                          case_sensitive=False))

    # Don't show the logged in user in the search
    query &= (atable.id != session.user_id)

    # Don't show users who have sent friend requests
    # to the logged in user
    tmprows = db(frtable.from_h != session.user_id).select(frtable.from_h)
    for row in tmprows:
        query &= (atable.id != row.from_h)

    rows = db(query).select()

    t = TABLE(_class="table")
    tr = TR(TH("Name"),
            TH("StopStalk Handle"))

    for site in current.SITES:
        tr.append(TH(site + " Handle"))

    tr.append(TH("Friendship Status"))
    t.append(tr)

    for user in rows:

        friends = db(db.friends.user_id == user.id).select().first()
        friends = eval(friends.friends_list)
        tr = TR()
        tr.append(TD(user.first_name + " " + user.last_name))
        tr.append(TD(user.stopstalk_handle))

        for site in current.SITES:
            tr.append(TD(user[site.lower() + "_handle"]))

        # Check if the current user is already a friend or not
        if session.user_id not in friends:
            r = db((frtable.from_h == session.user_id) &
                   (frtable.to_h == user.id)).select()
            if len(r) == 0:
                tr.append(TD(FORM(INPUT(_type="submit",
                                        _value="Add Friend",
                                        _class="btn btn-warning"),
                                  _action=URL("default", "mark_friend",
                                              args=[user.id]))))
            else:
                tr.append(TD("Friend request sent"))
        else:
            tr.append(TD("Already friends"))
        t.append(tr)

    return dict(t=t)

# ----------------------------------------------------------------------------
@auth.requires_login()
def submissions():
    """
        Retrieve submissions of the logged-in user
    """

    if len(request.args) == 0:
        active = "1"
    else:
        active = request.args[0]

    # Retrieve all the custom users created by the logged-in user
    query = (db.custom_friend.user_id == session.user_id)
    custom_friends = db(query).select(db.custom_friend.id)

    cusfriends = []
    for friend in custom_friends:
        cusfriends.append(friend.id)

    # Get the friends of logged in user
    query = (db.friends.user_id == session.user_id)
    friends = db(query).select(db.friends.friends_list).first()
    friends = tuple(eval(friends.friends_list))

    query = (db.submission.user_id.belongs(friends))
    query |= (db.submission.custom_user_id.belongs(cusfriends))
    total_count = db(query).count()

    PER_PAGE = current.PER_PAGE
    count = total_count / PER_PAGE
    if total_count % PER_PAGE:
        count += 1

    all_friends = []
    for friend_id in friends:
        row = db(db.auth_user.id == friend_id).select().first()
        all_friends.append([friend_id,
                            row.first_name + " " + row.last_name])

    all_custom_friends = []
    for friend_id in cusfriends:
        row = db(db.custom_friend.id == friend_id).select().first()
        all_custom_friends.append([friend_id,
                                   row.first_name + " " + row.last_name])

    if request.extension == "json":
        return dict(count=count,
                    friends=all_friends,
                    cusfriends=all_custom_friends)

    offset = PER_PAGE * (int(active) - 1)
    # Retrieve only some number of submissions from the offset
    rows = db(query).select(orderby=~db.submission.time_stamp,
                            limitby=(offset, offset + PER_PAGE))

    table = utilities.render_table(rows)
    return dict(table=table,
                friends=friends,
                cusfriends=cusfriends)

def start_retrieving():
    """
        AJAX helper function for starting retrieval
        of a particular user
    """

    if len(request.args) < 2:
        return "Failure"
    else:
        friend_id = int(request.args[0])
        custom = int(request.args[1])
        if custom == 1:
            custom = True
        else:
            custom = False

        result = utilities.retrieve_submissions(friend_id, custom)
        if result == "FAILURE":
            return "Failure"
        else:
            return result

# ----------------------------------------------------------------------------
def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()
