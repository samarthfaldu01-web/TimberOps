document.addEventListener("DOMContentLoaded", function () {

    // =====================================================
    // SIDEBAR TOGGLE
    // =====================================================

    const sidebar = document.getElementById(
        "sidebar"
    );

    const mainContainer = document.getElementById(
        "main-container"
    );

    const sidebarToggle = document.getElementById(
        "sidebar-toggle"
    );


    if (
        sidebarToggle
        && sidebar
        && mainContainer
    ) {

        sidebarToggle.addEventListener(
            "click",
            function () {

                sidebar.classList.toggle(
                    "collapsed"
                );

                mainContainer.classList.toggle(
                    "sidebar-collapsed"
                );
            }
        );
    }


    // =====================================================
    // UNFINISHED NAVIGATION BUTTONS
    // =====================================================

    document.querySelectorAll(
        ".coming-soon"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                alert(
                    button.dataset.feature
                    + " will be added later."
                );
            }
        );
    });


    // =====================================================
    // DELETE CONFIRMATION
    // =====================================================

    document.querySelectorAll(
        ".delete-form"
    ).forEach(function (form) {

        form.addEventListener(
            "submit",
            function (event) {

                const deleteButton = form.querySelector(
                    ".delete-button"
                );

                const itemName = deleteButton
                    ? deleteButton.dataset.itemName
                    : "this item";

                const confirmed = window.confirm(
                    "Delete "
                    + itemName
                    + " permanently?"
                );

                if (!confirmed) {
                    event.preventDefault();
                }
            }
        );
    });


    // =====================================================
    // FLASH MESSAGE CLOSE BUTTON
    // =====================================================

    document.querySelectorAll(
        ".close-flash"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const message = button.closest(
                    ".flash-message"
                );

                if (message) {
                    message.remove();
                }
            }
        );
    });

});