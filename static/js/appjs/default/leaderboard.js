(function($) {
    "use strict";

    var getVars = function() {
        // @Todo: Better and generalised way to do this?
        var url = window.location.href,
            params = url.split('?'),
            finalObject = {},
            param;

        if (params.length == 1) {
            return {};
        }

        params = params.splice(-1)[0];
        params = params.split('&');
        $.each(params, function(key, value) {
            param = value.split('=');
            finalObject[param[0]] = param[1];
        });
        return finalObject;
    };

    var getLeaderboardRows = function()  {
        $.ajax({
            method: 'GET',
            url: '/default/leaderboard_data.json',
            data: {'q': getParameterByName('q', window.location.href),
                   'global': getParameterByName('global', window.location.href)},
            success: function(response) {
                $('#leaderboard-heading').html(response["heading"]);
                $('title')[0].text = response["heading"];
                $.ajax({
                    method: 'GET',
                    url: '/static/css/partials/leaderboard-partial.html',
                    success: function(htmlResponse) {
                        var allUsers = response["users"].map(function(row) {
                            return {
                                        user_rank: row[0],
                                        user_name: row[1],
                                        user_stopstalk_handle: row[2],
                                        user_institute: row[3],
                                        user_rating: row[4],
                                        user_per_day_change: row[5],
                                        user_custom: row[6],
                                        user_rating_change: row[7],
                                        user_country: row[8]
                                    };
                        });
                        var renderedLeaderboard = Mustache.render(htmlResponse, {leaderboardRows: allUsers});
                        $('#leaderboard-content').html(renderedLeaderboard);

                    },
                    error: function(err) {

                    }
                });
                console.log(response);
            },
            error: function(err) {
                console.log(err);
            }
        });
    };

    $(document).ready(function() {

        getLeaderboardRows();

        $('#submission-switch').click(function() {
            var global = this.checked;
            var redirectURL = null;
            var params = getVars();
            var currentURL = window.location.href;
            if (global) {
                params['global'] = 'True';
            } else {
                params['global'] = 'False';
            }
            var parameterString = "";
            $.each(params, function(key, value) {
                parameterString += key + '=' + value + '&';
            });
            window.location.href = currentURL.split('?')[0] + '?' + parameterString.slice(0, -1);
        });
    });
})(jQuery);