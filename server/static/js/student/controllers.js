
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



app.controller("SubmissionDetailCtrl", ['$scope', '$window', '$location', '$stateParams', '$sce', '$timeout', '$anchorScroll', 'Submission',
  function($scope, $window, $location, $stateParams, $sce, $timeout, $anchorScroll, Submission) {
      var converter = new Showdown.converter();
      $scope.convertMarkdown = function(text) {
        if (text == "" || text === undefined) {
          return $sce.trustAsHtml("")
        }
        return $sce.trustAsHtml(converter.makeHtml(text));
      }

     Submission.get({
      id: $stateParams.submissionId
     }, function (response) {
        $scope.submission = response;
        $scope.courseId = $stateParams.courseId;
        if (response.messages && response.messages.file_contents && response.messages.file_contents['submit']) {
          delete $scope.submission.messages.file_contents['submit'];
          $scope.isSubmit = true;
        }

        if ($scope.submission.messages && $scope.isSubmit && !$scope.submission.assignment.active) {
          $scope.isSubmit = true;
          Submission.diff({id: $stateParams.submissionId},
            function(results) {
            $scope.diff = results;
            numbers = [];
            code = $scope.submission.messages.file_contents;
            commStart = '<div class="comment-template"><div class="comment"><span class="comment-icon"></span><div class="comment-content"><div class="comment-text">';
            commEnd = '</div></div></div></div>';
            for (var key in code) {
                if ($scope.diff.comments[key]) {
                    commentList = $scope.diff.comments[key];
                    file = code[key];
                    html = "";
                    if (file === file.toString()) {
                      for (i=0;i<file.split('\n').length;i++) {
                          comments = '';
                          if (commentList[i]) { // Ugly hack. Replace with TR based approach!
                              comments += commStart + '<h3>'+ commentList[i][0].author.email[0] + ' commented on line ' + (commentList[i][0].line).toString() + ': </h3> <p>' +
                                  $scope.convertMarkdown(commentList[i][0].message)+'</p>' + commEnd
                          }
                          html += '<div class="line">'+(i+1)+comments+'</div>';
                      }
                      numbers.push(html);
                    }
                }
            }

            $('code').each(function(i, block) {
                $(this).parent().find('.num-cont ul').html(numbers.shift());
                hljs.highlightBlock(block);
            });

            });
        } else {
          $timeout(function() {

            numbers = [];
            code = $scope.submission.messages.file_contents;

            for (var key in code) {
                if (code.hasOwnProperty(key)) {
                    comments = {}; // change this to ACTUAL dictionary of comments
                    file = code[key];
                    if (file && file === file.toString()) {
                        html = "";
                        for (i=0;i<file.split('\n').length;i++) {
                            comments = '';
                            html += '<div class="line">'+(i+1)+comments+'</div>';
                         }
                        numbers.push(html);
                      }
                }
            }


              $('code').each(function(i, block) {
                $(this).parent().find('.num-cont ul').html(numbers.shift());
                  hljs.highlightBlock(block);
              });
          }, 100);

        }

      }, function (error) {
        $window.swal("Uhoh", "There was an error!", "error");
      });
  }]);


// Main dashboard controller. Should be modularized later.
app.controller("AssignmentDashController", ['$scope', '$window', '$state',  '$stateParams', 'Assignment', 'User', 'Group', 'Submission', '$timeout',
  function($scope, $window, $state,  $stateParams, Assignment, User, Group, Submission, $timeout) {
      $scope.courseId = $stateParams.courseId

      $scope.reloadAssignments = function () {
          User.get({
            course: $stateParams.courseId,
          }, function (response) {
            $scope.closeDetails();
            $scope.assignments = response.assignments;
            for (i = 0;i<response.assignments.length;i++) {
                $scope.assignInit(response.assignments[i]);
            }
          }, function (error) {
            $window.swal('Unknown Course', 'Whoops. There was an error', 'error');
            $state.transitionTo('courseLanding', null, { reload: true, inherit: true, notify: true })
          })
      }
      $scope.assignInit = function(assign) {
        if (assign.backups) {
            $scope.getBackups(assign, false);
        }
        if (assign.submissions) {
            $scope.getSubmissions(assign, false);
        }
      }
      $scope.showComposition = function(score, backupId) {
        if (score) {
          $window.swal({title: 'Score: '+score.score+'/2',
              text: 'Message: ' + score.message,
              showCancelButton: false,
              icon: false,
              allowEscapeKey: true,
              allowOutsideClick: true,
              confirmButtonText: "View Comments",
              closeOnConfirm: false},
              function(isConfirm){
                if (isConfirm) {
                  $window.location.replace('/old#/submission/'+backupId.toString()+'/diff')
                } else {

                } });
        }
      }
      $scope.reloadView = function () {
        // oldToggle = $scope.currAssign.id
        $state.transitionTo($state.current, angular.copy($stateParams), { reload: true, inherit: true, notify: true });
      };

      $scope.reloadAssignments()

      $scope.removeMember = function(currGroup, member) {
            Group.removeMember({
              id: currGroup.id,
              email: member.email[0]
            }, function (err) {
                $scope.reloadView()
                $scope.currGroup = null;
                $scope.currAssign.group = null
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

      $scope.subm_quantity = 10;
      $scope.backup_quantity = 10;


      $scope.getSubmissions = function (assign,toIncrease) {
            if (toIncrease) {
              $scope.subm_quantity += 50;
            }
            console.log(assign.assignment.id);
            User.getSubmissions({
              assignment: assign.assignment.id,
              quantity: $scope.subm_quantity
            }, function (response) {
              assign.submissions = response;
            });
            console.log(assign.submissions);
      }

      $scope.getBackups = function (assign, toIncrease) {
            if (toIncrease) {
              $scope.backup_quantity += 50;
            }
            User.getBackups({
              assignment: assign.assignment.id,
              quantity: $scope.backup_quantity
            }, function (response) {
                assign.backups = response;
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
      
      $scope.randomColor = function randomColor(assignment) {
        themes = ['blue','gold','green']
        if (!assignment.color) {
            assignment.color = themes[Math.ceil(Math.random()*themes.length)-1]
        }
        return assignment
      }

        $scope.openDetails = function openDetails(assign) {
            $scope.currGroup = assign.group
            $scope.currAssign = assign
            $('.container-fluid').addClass('active');
            $('.sidebar[id="'+assign.assignment.id+'"]').addClass('active');
        }
        
        $scope.closeDetails = function closeDetails() {
            $('.sidebar').removeClass('active');
            $('.container-fluid').removeClass('active');
        }
      } 
]);

// copied from admin
app.controller("DiffController", ["$scope", "$timeout", "$location", "$anchorScroll", "$sce",
  function ($scope, $timeout, $location, $anchorScroll, $sce) {
    contents = [];
    var leftNum = 0, rightNum = 0;
    for (var i = 0; i < $scope.contents.length; i++) {
      codeline = {"type": "line"};
      codeline.start = $scope.contents[i][0];
      codeline.line = $scope.contents[i].slice(2);
      codeline.index = i;
      // Only care about right-num (which is the new-file)
      if ($scope.diff.comments.hasOwnProperty($scope.file_name) && $scope.diff.comments[$scope.file_name].hasOwnProperty(rightNum)) {
        codeline.comments = $scope.diff.comments[$scope.file_name][rightNum]
      }
      codeline.lineNum = i + 1;
      if (codeline.start == "+") {
        rightNum++;
        codeline.rightNum = rightNum;
        codeline.leftNum = "";
      } else if (codeline.start == "-") {
        leftNum++;
        codeline.leftNum = leftNum;;
        codeline.rightNum = "";
      } else if (codeline.start == "?") {
          // TODO: add in-line coloring
          continue;
        } else {
          leftNum++;
          rightNum++;
          codeline.leftNum = leftNum;;
          codeline.rightNum = rightNum;
        }
        contents.push(codeline);
      }
      $scope.contents = contents;
      $timeout(function() {
        $(".diff-line-code").each(function(i, elem) {
          hljs.highlightBlock(elem);
        });
        $anchorScroll();
      });
    }
    ]);

// copied from admin
app.controller("DiffLineController", ["$scope", "$timeout", "$location", "$anchorScroll", "$sce", "$modal",
  function ($scope, $timeout, $location, $anchorScroll, $sce, $modal) {
    var converter = new Showdown.converter();
    $scope.convertMarkdown = function(text) {
      if (text == "" || text === undefined) {
        return $sce.trustAsHtml("")
      }
      return $sce.trustAsHtml(converter.makeHtml(text));
    }
    var start = $scope.codeline.start;
    if (start == "+") {
      $scope.positive = true;
    } else if (start == "-") {
      $scope.negative = true;
    } else {
      $scope.neutral = true;
    }
    $scope.anchorId = $scope.file_name + "-L" + $scope.codeline.lineNum;

    $scope.scroll = function() {
      //$location.hash($scope.anchorId);
      // $anchorScroll();
    }

    $scope.showComment = false;
    $scope.hideBox = false;
    $scope.showWriter = true;
    $scope.toggleComment = function() {
      $scope.showComment = !$scope.showComment;
    }
    $scope.toggleBox = function() {
      $scope.hideBox = !$scope.hideBox;
    }
    $scope.toggleWriter = function() {
      $scope.showWriter = !$scope.showWriter;
    }
  }
  ]);
  
  // copied from admin
  app.controller("CommentController", ["$scope", "$window", "$stateParams", "$timeout", "$modal", "Submission",
    function ($scope, $window, $stateParams, $timeout, $modal, Submission) {
      $scope.remove = function() {
        var modal = $modal.open({
          templateUrl: '/static/partials/common/removecomment.modal.html',
          scope: $scope,
          size: 'sm',
          resolve: {
            modal: function () {
              return modal;
            }
          }
        });
        modal.result.then(function() {
          Submission.deleteComment({
            id: $scope.backupId,
            comment: $scope.comment.id
          }, function (result){
            $scope.toggleBox()
            $scope.comment = false;
          });
        });
      }
    }
    ]);
  
  // copied from admin
  app.controller("WriteCommentController", ["$scope", "$sce", "$stateParams", "Submission",
    function ($scope, $sce, $stateParams, Submission) {
      var converter = new Showdown.converter();
      $scope.convertMarkdown = function(text) {
        if (text == "" || text === undefined) {
          return $sce.trustAsHtml("No comment yet...")
        }
        return $sce.trustAsHtml(converter.makeHtml(text));
      }
      $scope.commentText = {text:""}
      $scope.makeComment = function() {
        text = $scope.commentText.text;
        if (text !== undefined && text.trim() != "") {
          Submission.addComment({
            id: $scope.backupId,
            file: $scope.file_name,
            index: $scope.codeline.rightNum - 1,
            message: text,
          }, function (resp) {
            resp.self = true
            if ($scope.codeline.comments) {
              $scope.codeline.comments.push(resp)
            } else {
              $scope.codeline.comments = [resp]
            }
            $scope.toggleWriter()
          });
        }
      }
    }
    ]);