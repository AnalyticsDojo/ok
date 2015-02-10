
app.controller("CourseSelectorController", ["$scope", "$window", "$state", '$stateParams', 'Course',
    function ($scope, $window, $state, $stateParams, Course) {
      Course.get(function(response) {
        $scope.courses = response.results
      });
      if ($window.user.indexOf("berkeley.edu") == -1) {
        $window.swal({
            title: "Is this the right login?",
            text: "Logging you in with your \"" + $window.user + "\" account...",
            type: "info",
            showCancelButton: true,
            confirmButtonColor: "#DD6B55",
            confirmButtonText: "Yes - that's correct!",
            cancelButtonText: "No - log me out",
            closeOnConfirm: true,
            closeOnCancel: true
        }, function(isConfirm) {
            if (isConfirm) {
              // Do nothing, because the user might want to select a course.
            } else {
                $window.location.href = $window.reloginLink;
            }
        });
      } else {
         $window.location.hash = "";
      }
    }
]);

// Assignment Controllers
app.controller("AssignmentOverviewController", ['$scope', 'Assignment', 'User', '$timeout',
  function($scope, Assignment, User, $timeout) {
    Assignment.query({
      fields: {
        id: true,
        display_name: true,
        id: true,
        due_date: true,
        points: true,
        created: true,
      }}, function(response) {
      $scope.assignments = response.results;
    })}
]);

// Assignment Controllers
app.controller("GroupOverviewController", ['$scope', 'Assignment', 'User', '$timeout',
  function($scope, Assignment, User, $timeout) {
    Group.query(function(response) {
      $scope.assignments = response.results;
    })}
]);



app.controller("SubmissionDetailCtrl", ['$scope', '$window', '$location', '$stateParams',  '$timeout', '$anchorScroll', 'Submission',
  function($scope, $window, $location, $stateParams, $timeout, $anchorScroll, Submission) {
     Submission.get({id: $stateParams.submissionId}, function (response) {
        $scope.submission = response;
        $scope.courseId = $stateParams.courseId;
        if ($scope.submission.messages && $scope.submission.messages.file_contents['submit']) {
          $scope.isSubmit = true;
          delete $scope.submission.messages.file_contents['submit'];
        }

        sample_comments = {'hog.py':
            {
                20: {'name': 'Johnny Appleseed', 'message': 'Hello.', 'replies':
                    [{'name': 'Anonymous', 'message': 'Ewieeeee.'}]},
                40: {'name': 'YoyoMa', 'message': 'HAH'}
            }
        }

        $timeout(function() {

            numbers = [];
            code = $scope.submission.messages.file_contents;
            commtemp = $('.comment-template').html();
            $('.comment-template').delete();
            
            for (var key in code) {
                if (code.hasOwnProperty(key)) {
                    comments = sample_comments; // change this to ACTUAL dictionary of comments
                    file = code[key];
                    for (i=0;i<file.split('\n').length;i++) {
                        comments = html = '';
                        if (comments.hasOwnProperty(i)) {
                            comments += commtemp;
                        }
                        html += '<p>'+(i+1)+(comments || "")+'</p>';
                    }
                    numbers.push(html);
                }
            }

            $('code').each(function(i, block) {
                $(this).parent().find('.num-cont ul').html(numbers.shift());
                hljs.highlightBlock(block);
            });
        }, 100);
      }, function (error) {
        $window.swal("Uhoh", "There was an error!", "error");
      });
  }]);


// Main dashboard controller. Should be modularized later.
app.controller("AssignmentDashController", ['$scope', '$window', '$state',  '$stateParams', 'Assignment', 'User', 'Group', 'Submission', '$timeout',
  function($scope, $window, $state,  $stateParams, Assignment, User, Group, Submission, $timeout) {
      $scope.courseId = $stateParams.courseId

      $scope.toggleAssign = function (assign) {
        if ($scope.currAssign == assign) {
          $scope.currAssign = null
        } else {
          $scope.currAssign = assign;
        }
      }

      $scope.findAndToggle = function (assignId) {
        for (var i = 0; i < $scope.assignments.length; i++) {
          if ($scope.assignments[i].id == assignId) {
            $scope.toggleAssign($scope.assignments[i])
          }
        }
      }

      $scope.reloadAssignments = function () {
        $scope.showLoader()
          User.get({
            course: $stateParams.courseId,
          }, function (response) {
            $scope.assignments = response.assignments
            $scope.hideLoader()
          }, function (error) {
            $scope.hideLoader()
            $window.swal('Unknown Course', 'Whoops.', 'error');
            $state.transitionTo('courseLanding', null, { reload: true, inherit: true, notify: true })
          })
      }

      $scope.reloadView = function () {
        // oldToggle = $scope.currAssign.id
        $state.transitionTo($state.current, angular.copy($stateParams), { reload: true, inherit: true, notify: true });
      };

      $scope.showLoader = function showLoader() {
        $('.loader').removeClass('hide');
      }

      $scope.hideLoader = function hideLoader() {
        $('.loader').addClass('done hide');
        setTimeout(function() {
          $('.loader').removeClass('done')
        },800)
      }

      $scope.reloadAssignments()

      $scope.removeMember = function(currGroup, member) {
            Group.removeMember({
              id: currGroup.id,
              email: member.email[0]
            }, function (err) {
              $scope.hideGroup();
              if (member.email[0] != $window.user) {
                  $scope.reloadView()
              } else {
                $scope.currGroup = null;
                $scope.currAssign.group = null

              }
            });
      };

      $scope.winRate = function (assign, backupId) {
        assign.winrate = {'progress': 1, 'message': "Loading"}
        Submission.winRate({
          id: backupId
        }, function (response){
          if (response.error.type) {
            assign.winrate = {'progress': 0, 'error': true, 'message': response.error.type+" Error"}
            $window.swal(response.error.type + " Error",'There was a ' + response.error.type + ' error in your code.','error')
          } else {
            $scope.winrate = response
            assign.winrate = {
              'progress': (response.winrate / .56) * 100,
              'percent': response.winrate * 100,
              'message': response.message
            }
          }
          // $window.swal(response.winrate*100 +"%",'Final Win Rate','info')
        }, function (err) {
          assign.winrate = {
            'message': response.message,
            'error': true
          }

          $window.swal("Uhoh",'There was an error','error')
        });
      }

      $scope.rejectInvite = function(currGroup) {
          Group.rejectInvitation({
            id: currGroup.id,
          }, function (err) {
            currGroup = null
            $scope.currAssign.group = null
          });
      };

      $scope.acceptInvite = function(currGroup) {
          Group.acceptInvitation({
              id: currGroup.id,
          }, function (err) {
            $scope.reloadView()
          });
      };

      $scope.getSubmissions = function (assignId) {
            User.getSubmissions({
              assignment: assignId
            }, function (response) {
              $scope.currAssign.submissions = response;
              $scope.showSubms();
            });
      }

      $scope.getBackups = function (assignId) {
            User.getBackups({
              assignment: assignId
            }, function (response) {
              $scope.currAssign.backups = response;
              $scope.showBackups();
            });
      }


      $scope.addMember = function(assign, member) {
        if (member && member != '') {
          assignId = assign.assignment.id
          Assignment.invite({
            id: assignId,
            email: member
          }, function (response) {
              $scope.reloadView()
              $window.swal({
                  title: "Invitation Sent!",
                  text: "They will need to login to okpy.org and accept the invite.",
                  timer: 3500,
                  type: "success"
                });

          }, function (err) {
            $window.swal("Oops...", "Can't add that user to your group.    Is that the right email? They might already be in a group or may not be in the course.", "error");
         });
        }
      };

      $scope.showGroup = function showGroup(group) {
          $('.popups').addClass('active');
          $('.popup').removeClass('active');
          $('.popup.group').addClass('active').removeClass('hide');
          $scope.currGroup = group
      }

      $scope.hideGroup = function hideGroup() {
          $('.popups').removeClass('active');
          $('.popup').removeClass('active');
          $('.popup.group').addClass('active').addClass('hide');
      }

      $scope.showBackups = function showGroup(id) {
          $('.popups').addClass('active');
          $('.popup').removeClass('active');
          $('.popup.backups').addClass('active').removeClass('hide');
      }

      $scope.showSubms = function showGroup(id) {
          $('.popups').addClass('active');
          $('.popup').removeClass('active');
          $('.popup.submissions').addClass('active').removeClass('hide');
      }

      $scope.hidePopups =  function hidePopups() {
          $('.assign').removeClass('s');
          $('.popups').removeClass('active');
          $('.popup').removeClass('active');
          setTimeout(function() {
            $('.popup').addClass('hide');
          },400);
        }


      }
]);


