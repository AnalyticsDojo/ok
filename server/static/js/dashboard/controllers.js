app.controller("AssignmentModuleController", ["$scope", "Assignment",
    function ($scope, Assignment) {
      Assignment.query({
        active: true,
      }, function(response) {
        $scope.assignments = response.results;
      });
    }
  ]);

app.controller("SubmissionDashboardController", ["$scope", "Submission",
    function ($scope, Submission) {
      $scope.itemsPerPage = 3;
      $scope.currentPage = 1;
      $scope.getPage = function(page) {
      Submission.query({
        fields: {
          'created': true,
          'db_created': true,
          'id': true,
          'submitter': {
            'id': true
          },
          'tags': true,
          'assignment': {
            'name': true,
            'display_name': true,
            'id': true,
          },
          'messages': {
            'file_contents': "presence"
          }
        },
        page: page,
        num_page: $scope.itemsPerPage,
        "messages.kind": "file_contents"
      }, function(response) {
          $scope.submissions = response.data.results;
          if (response.data.more) {
            $scope.totalItems = $scope.currentPage * $scope.itemsPerPage + 1;
          } else {
            $scope.totalItems = ($scope.currentPage - 1) * $scope.itemsPerPage + response.data.results.length;
          }
        });
      }
      $scope.pageChanged = function() {
        $scope.getPage($scope.currentPage);
      }
      $scope.getPage(1);
    }
  ]);


app.controller("CourseModuleController", ["$scope",
    function ($scope) {
      $scope.course_name = "CS 61A";
      $scope.course_desc = "Structure and Interpretation of Computer Programs";
    }
  ]);

