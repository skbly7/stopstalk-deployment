"""
    Copyright (c) 2015-2016 Raj Patel(raj454raj@gmail.com), StopStalk

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.
"""
ptable = db.problem_tags
stable = db.submission

print "Retrieving problems from DB..."
problems = db(ptable).select()
print "DB query done..."

final_dict = {}

print "Iterating through problems..."
for problem in problems:
    final_dict[problem.problem_link] = {"id": problem.id,
                                        "submissions": 0,
                                        "accepted": 0,
                                        "users": set([]),
                                        "custom_users": set([])}
print "Iterating problems done..."

BATCH_SIZE = 10000
start = 0

for i in xrange(1000):
    print "Processing Batch #%d" % (i + 1)
    submissions = db(stable).select(stable.problem_link,
                                    stable.user_id,
                                    stable.custom_user_id,
                                    stable.status,
                                    limitby=(start, start + BATCH_SIZE))
    if len(submissions) == 0:
        break
    start += BATCH_SIZE

    print "Iterating through submissions..."
    for submission in submissions:
        prob = final_dict[submission.problem_link]
        prob["submissions"] += 1
        if submission.status == "AC":
            prob["accepted"] += 1
        if submission.user_id:
            prob["users"].add(submission.user_id)
        else:
            prob["custom_users"].add(submission.custom_user_id)
    print "Iterating submissions done..."

for plink in final_dict:
    if final_dict[plink]["submissions"] == 0:
        continue
    accuracy = (len(final_dict[plink]["users"]) + \
                len(final_dict[plink]["custom_users"])) * 1.0 / \
               final_dict[plink]["submissions"]
    print "%s,%s,%d" % (plink,
                        str(accuracy),
                        final_dict[plink]["submissions"])
