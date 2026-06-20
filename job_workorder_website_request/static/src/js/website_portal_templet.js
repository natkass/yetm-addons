/*
odoo.define('job_workorder_website_request.website_portal_templet', function(require) {

$(document).ready(function(){
    console.log('abcd')
    
    $(".myInput").change(function myFunction() {
          console.log('==========================')
          var input, filter, table, tr, td, i;
          console.log("--------------",input , filter, table, tr, td , i)
          input = document.getElementById("myInput");
          console.log("input==============",input)
          filter = input.value.toUpperCase();
          console.log("filter==============",filter)
          table = document.getElementById("joborder_table");
          console.log("table==============",table)
          tr = table.getElementsByTagName("tr");
          console.log("tr==============",tr)
          for (i = 0; i < tr.length; i++) {
            td = tr[i].getElementsByTagName("td")[0];
            if (td) {
              if (td.innerHTML.toUpperCase().indexOf(filter) > -1) {
                tr[i].style.display = "";
              } else {
                tr[i].style.display = "none";
              }
            }       
          }
        });

    });

}); 
*/
