function previewImage(event) {

    const image = event.target.files[0];

    const preview = document.getElementById("preview");

    if (!image) {
        preview.style.display = "none";
        return;
    }

    preview.src = URL.createObjectURL(image);

    preview.style.display = "block";
}


function validateReportForm() {

    const imageInput = document.getElementById("image");

    if (imageInput.files.length === 0) {
        alert("Please select a road image.");
        return false;
    }

    const image = imageInput.files[0];

    const maxSize = 5 * 1024 * 1024;

    if (image.size > maxSize) {
        alert("Image must be less than 5 MB.");
        return false;
    }

    return true;
}


function confirmDelete() {

    return confirm(
        "Are you sure you want to delete this report?"
    );
}