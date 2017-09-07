$(function(){
    // To prevent Browsers from opening the file when its dragged and dropped on to the page
    $(document).on('drop dragover', function (e) { e.preventDefault(); });

    // Add events
    $('input[type=file]').on('change', fileUpload);
    facesData = [];
    file = null;
    // File uploader function
    function fileUpload(event){
        files = event.target.files;
        var data = new FormData();
        file = files[0];
        data.append('image', file, file.name);

        function do_faces() {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/faces', true);
            xhr.send(data);
            xhr.onload = function () {
                facesData = JSON.parse(this.responseText);

            };
        }

        function do_faces_landmarks() {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/faces-landmarks', true);
            xhr.send(data);
            xhr.onload = function () {
                facesData = JSON.parse(this.responseText)
                for (var i = 0; i < facesData.length; i ++ ) {
                    var face = facesData[i];
                    ctx.lineWidth = "3";
                    ctx.strokeStyle = 'red';
                    ctx.strokeRect(face.left, face.top, face.right-face.left, face.bottom-face.top);
                    ctx.strokeStyle = 'green';
                    function do_from(ctx, start, end, close) {
                        ctx.beginPath();
                        var point = face.landmark_68[start];
                        ctx.moveTo(point[0], point[1]);
                        for (var j=start; j <= end; j++) {
                            point = face.landmark_68[j];
                            ctx.lineTo(point[0], point[1]);
                        }
                        if (close) {
                            point = face.landmark_68[start];
                            ctx.lineTo(point[0], point[1]);
                        }
                        ctx.stroke();
                    }

                    //chin
                    do_from(ctx, 0, 16);
                    do_from(ctx, 17, 21);
                    do_from(ctx, 22, 26);
                    do_from(ctx, 27, 30);
                    do_from(ctx, 31, 35);
                    do_from(ctx, 36, 41, true);
                    do_from(ctx, 42, 47, true);
                    do_from(ctx, 48, 67, true);
                }
            };
        }

        $("#faces").off("click").click(do_faces);
        $("#faces-landmarks").off("click").click(do_faces_landmarks);
        try {
            document.getElementById("canvas").remove()
            $("#clear").off("click");
        } catch(e){}
        var fr = new FileReader();
        fr.onload = function () {
            img = document.getElementById("image");
            img.src = fr.result;
            img.onload = function(){
                canvas = document.createElement('canvas');
                canvas.id = 'canvas';
                canvas.width  = img.width;
                canvas.height = img.height;
                document.body.appendChild(canvas)
                ctx = canvas.getContext('2d')
                ctx.fillStyle = 'black';
                ctx.strokeStyle = 'red';
                ctx.drawImage(img, 0, 0);
                $("#clear").click(function(){
                    ctx.drawImage(img, 0, 0);
                });
            }
        }
        fr.readAsDataURL(file);
    }
});