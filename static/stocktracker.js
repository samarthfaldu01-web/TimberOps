/*
==========================================================
File: stock_tracker.js
Project: TimberOps

Purpose:
Controls Stock Tracker modals, edit forms, stock adjustments,
delete confirmation and flash messages.
==========================================================
*/

document.addEventListener("DOMContentLoaded", function () {

    // =====================================================
    // MODAL FUNCTIONS
    // =====================================================

    const modals = document.querySelectorAll(".modal");

    function openModal(modal) {

        if (!modal) {
            return;
        }

        modal.classList.add("modal-open");

        modal.setAttribute(
            "aria-hidden",
            "false"
        );

        document.body.classList.add(
            "modal-active"
        );

        const firstInput = modal.querySelector(
            "input, select, textarea, button"
        );

        if (firstInput) {
            firstInput.focus();
        }
    }


    function closeModal(modal) {

        if (!modal) {
            return;
        }

        modal.classList.remove(
            "modal-open"
        );

        modal.setAttribute(
            "aria-hidden",
            "true"
        );

        document.body.classList.remove(
            "modal-active"
        );
    }


    // Closes modals using the X button or Cancel button.
    document.querySelectorAll(
        ".modal-close, .modal-cancel"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                closeModal(
                    button.closest(".modal")
                );

            }
        );

    });


    // Closes modals when the dark background is clicked.
    document.querySelectorAll(
        ".modal-background"
    ).forEach(function (background) {

        background.addEventListener(
            "click",
            function () {

                closeModal(
                    background.closest(".modal")
                );

            }
        );

    });


    // Closes the currently open modal when Escape is pressed.
    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Escape") {

                const openModalElement =
                    document.querySelector(
                        ".modal.modal-open"
                    );

                closeModal(
                    openModalElement
                );
            }

        }
    );


    // =====================================================
    // ADD STOCK MODAL
    // =====================================================

    const addStockButton = document.getElementById(
        "open-add-modal"
    );

    const addStockModal = document.getElementById(
        "add-stock-modal"
    );

    if (addStockButton && addStockModal) {

        addStockButton.addEventListener(
            "click",
            function () {

                openModal(
                    addStockModal
                );

            }
        );

    }


    // =====================================================
    // EDIT STOCK MODAL
    // =====================================================

    const editStockModal = document.getElementById(
        "edit-stock-modal"
    );

    const editStockForm = document.getElementById(
        "edit-stock-form"
    );

    document.querySelectorAll(
        ".edit-button"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const itemId =
                    button.dataset.itemId;

                editStockForm.action =
                    "/stock/"
                    + itemId
                    + "/edit";


                document.getElementById(
                    "edit-item-code"
                ).value =
                    button.dataset.itemCode;


                document.getElementById(
                    "edit-item-name"
                ).value =
                    button.dataset.itemName;


                document.getElementById(
                    "edit-category"
                ).value =
                    button.dataset.category;


                document.getElementById(
                    "edit-quantity"
                ).value =
                    button.dataset.quantity;


                document.getElementById(
                    "edit-minimum"
                ).value =
                    button.dataset.minimum;


                document.getElementById(
                    "edit-unit"
                ).value =
                    button.dataset.unit;


                document.getElementById(
                    "edit-location"
                ).value =
                    button.dataset.location;


                document.getElementById(
                    "edit-notes"
                ).value =
                    button.dataset.notes;


                openModal(
                    editStockModal
                );

            }
        );

    });


    // =====================================================
    // STOCK ADJUSTMENT MODAL
    // =====================================================

    const adjustStockModal = document.getElementById(
        "adjust-stock-modal"
    );

    const adjustStockForm = document.getElementById(
        "adjust-stock-form"
    );

    const adjustDescription = document.getElementById(
        "adjust-item-description"
    );

    document.querySelectorAll(
        ".adjust-button"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const itemId =
                    button.dataset.itemId;

                const itemName =
                    button.dataset.itemName;

                const currentQuantity =
                    button.dataset.currentQuantity;


                adjustStockForm.action =
                    "/stock/"
                    + itemId
                    + "/adjust";


                adjustDescription.textContent =
                    itemName
                    + " currently has "
                    + currentQuantity
                    + " in stock.";


                openModal(
                    adjustStockModal
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

                const deleteButton =
                    form.querySelector(
                        ".delete-button"
                    );

                const itemName =
                    deleteButton.dataset.itemName;

                const confirmed = window.confirm(
                    "Permanently delete "
                    + itemName
                    + "?\n\n"
                    + "This will also delete its stock history."
                );

                if (!confirmed) {
                    event.preventDefault();
                }

            }
        );

    });


    // =====================================================
    // AUTOMATIC FILTERING
    // =====================================================

    const filterForm = document.getElementById(
        "stock-filter-form"
    );

    const filterSelects = document.querySelectorAll(
        "#category-filter, #status-filter, #sort-filter"
    );

    filterSelects.forEach(function (select) {

        select.addEventListener(
            "change",
            function () {

                if (filterForm) {
                    filterForm.submit();
                }

            }
        );

    });


    // =====================================================
    // FLASH MESSAGES
    // =====================================================

    document.querySelectorAll(
        ".close-flash"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const message =
                    button.closest(
                        ".flash-message"
                    );

                if (message) {
                    message.remove();
                }

            }
        );

    });


    // Automatically removes flash messages after six seconds.
    window.setTimeout(
        function () {

            document.querySelectorAll(
                ".flash-message"
            ).forEach(function (message) {

                message.classList.add(
                    "flash-message-hidden"
                );

                window.setTimeout(
                    function () {
                        message.remove();
                    },
                    300
                );

            });

        },
        6000
    );

});