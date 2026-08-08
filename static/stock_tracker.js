document.addEventListener("DOMContentLoaded", function () {

    // =====================================================
    // ELEMENT REFERENCES
    // =====================================================

    const body = document.body;

    const sidebar = document.getElementById(
        "sidebar"
    );

    const mainContainer = document.getElementById(
        "main-container"
    );

    const sidebarToggle = document.getElementById(
        "sidebar-toggle"
    );


    const addModal = document.getElementById(
        "add-stock-modal"
    );

    const editModal = document.getElementById(
        "edit-stock-modal"
    );

    const adjustModal = document.getElementById(
        "adjust-stock-modal"
    );


    const openAddButton = document.getElementById(
        "open-add-modal"
    );

    const editForm = document.getElementById(
        "edit-stock-form"
    );

    const adjustForm = document.getElementById(
        "adjust-stock-form"
    );


    // =====================================================
    // REAL NAVIGATION LINKS
    // =====================================================

    document.querySelectorAll(
        ".sidebar-link"
    ).forEach(function (link) {

        const title = link.getAttribute(
            "title"
        );


        if (
            title === "Calendar"
            || title === "Job Scheduling"
        ) {

            link.addEventListener(
                "click",
                function (event) {

                    event.preventDefault();

                    window.location.href =
                        "/job-scheduling";
                }
            );
        }


        if (
            title === "Messages"
            || title === "Customer Job Request"
        ) {

            link.addEventListener(
                "click",
                function (event) {

                    event.preventDefault();

                    window.location.href =
                        "/job-request";
                }
            );
        }

    });


    // =====================================================
    // SIDEBAR BUTTON
    // =====================================================

    if (
        sidebarToggle
        && sidebar
        && mainContainer
    ) {

        sidebarToggle.addEventListener(
            "click",
            function () {

                const sidebarIsHidden =
                    sidebar.style.transform
                    === "translateX(-100%)";


                if (sidebarIsHidden) {

                    sidebar.style.transform =
                        "translateX(0)";

                    sidebar.style.transition =
                        "transform 0.25s ease";

                } else {

                    sidebar.style.transform =
                        "translateX(-100%)";

                    sidebar.style.transition =
                        "transform 0.25s ease";
                }
            }
        );
    }


    // =====================================================
    // MODAL FUNCTIONS
    // =====================================================

    function openModal(modal) {

        if (!modal) {
            return;
        }


        modal.hidden = false;

        modal.classList.add(
            "modal-open"
        );


        modal.setAttribute(
            "aria-hidden",
            "false"
        );


        body.classList.add(
            "modal-active"
        );


        const firstInput = modal.querySelector(
            "input:not([type='hidden']), select, textarea"
        );


        if (firstInput) {

            window.setTimeout(
                function () {

                    firstInput.focus();

                },
                50
            );
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


        modal.hidden = true;


        const anyOpenModal =
            document.querySelector(
                ".modal.modal-open"
            );


        if (!anyOpenModal) {

            body.classList.remove(
                "modal-active"
            );
        }
    }


    function closeAllModals() {

        document.querySelectorAll(
            ".modal"
        ).forEach(function (modal) {

            closeModal(
                modal
            );

        });
    }


    // =====================================================
    // ADD STOCK MODAL
    // =====================================================

    if (
        openAddButton
        && addModal
    ) {

        openAddButton.addEventListener(
            "click",
            function () {

                openModal(
                    addModal
                );
            }
        );
    }


    // =====================================================
    // EDIT STOCK MODAL
    // =====================================================

    document.querySelectorAll(
        ".edit-button"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                if (
                    !editModal
                    || !editForm
                ) {
                    return;
                }


                const itemCode =
                    document.getElementById(
                        "edit-item-code"
                    );


                const itemName =
                    document.getElementById(
                        "edit-item-name"
                    );


                const category =
                    document.getElementById(
                        "edit-category"
                    );


                const specification =
                    document.getElementById(
                        "edit-specification"
                    );


                const quantity =
                    document.getElementById(
                        "edit-quantity"
                    );


                const minimum =
                    document.getElementById(
                        "edit-minimum"
                    );


                const unit =
                    document.getElementById(
                        "edit-unit"
                    );


                const location =
                    document.getElementById(
                        "edit-location"
                    );


                const unitCost =
                    document.getElementById(
                        "edit-unit-cost"
                    );


                const notes =
                    document.getElementById(
                        "edit-notes"
                    );


                editForm.action =
                    button.dataset.editUrl;


                if (itemCode) {

                    itemCode.value =
                        button.dataset.itemCode
                        || "";
                }


                if (itemName) {

                    itemName.value =
                        button.dataset.itemName
                        || "";
                }


                if (category) {

                    category.value =
                        button.dataset.category
                        || "";
                }


                if (specification) {

                    specification.value =
                        button.dataset.specification
                        || "";
                }


                if (quantity) {

                    quantity.value =
                        button.dataset.quantity
                        || "0";
                }


                if (minimum) {

                    minimum.value =
                        button.dataset.minimum
                        || "0";
                }


                if (unit) {

                    unit.value =
                        button.dataset.unit
                        || "";
                }


                if (location) {

                    location.value =
                        button.dataset.location
                        || "";
                }


                if (unitCost) {

                    unitCost.value =
                        button.dataset.unitCost
                        || "0";
                }


                if (notes) {

                    notes.value =
                        button.dataset.notes
                        || "";
                }


                openModal(
                    editModal
                );
            }
        );
    });


    // =====================================================
    // STOCK ADJUSTMENT MODAL
    // =====================================================

    document.querySelectorAll(
        ".adjust-button"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                if (
                    !adjustModal
                    || !adjustForm
                ) {
                    return;
                }


                adjustForm.action =
                    button.dataset.adjustUrl;


                const description =
                    document.getElementById(
                        "adjust-item-description"
                    );


                const movement =
                    document.getElementById(
                        "adjust-movement"
                    );


                if (movement) {

                    movement.value =
                        "in";
                }


                if (description) {

                    const itemName =
                        button.dataset.itemName
                        || "Selected item";


                    const currentQuantity =
                        button.dataset.currentQuantity
                        || "0";


                    const unit =
                        button.dataset.unit
                        || "units";


                    description.textContent =
                        itemName
                        + " currently has "
                        + currentQuantity
                        + " "
                        + unit
                        + ".";
                }


                openModal(
                    adjustModal
                );
            }
        );
    });


    // =====================================================
    // CLOSE MODAL BUTTONS
    // =====================================================

    document.querySelectorAll(
        ".modal-close, .modal-cancel"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const modal =
                    button.closest(
                        ".modal"
                    );


                closeModal(
                    modal
                );
            }
        );
    });


    // =====================================================
    // CLOSE MODAL BY CLICKING BACKGROUND
    // =====================================================

    document.querySelectorAll(
        ".modal-background"
    ).forEach(function (background) {

        background.addEventListener(
            "click",
            function () {

                const modal =
                    background.closest(
                        ".modal"
                    );


                closeModal(
                    modal
                );
            }
        );
    });


    // =====================================================
    // ESCAPE KEY
    // =====================================================

    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key
                === "Escape"
            ) {

                closeAllModals();
            }
        }
    );


    // =====================================================
    // OPEN SERVER-REQUESTED MODALS
    // =====================================================

    document.querySelectorAll(
        ".modal[data-open-on-load='true']"
    ).forEach(function (modal) {

        openModal(
            modal
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
                    deleteButton
                        ? deleteButton.dataset.itemName
                        : "this item";


                const confirmed =
                    window.confirm(
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
    // FLASH MESSAGE CLOSE
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


                if (!message) {
                    return;
                }


                message.classList.add(
                    "flash-message-hidden"
                );


                window.setTimeout(
                    function () {

                        message.remove();

                    },
                    300
                );
            }
        );
    });


    // =====================================================
    // UNFINISHED NAVIGATION
    // =====================================================

    document.querySelectorAll(
        ".coming-soon"
    ).forEach(function (button) {

        const title =
            button.getAttribute(
                "title"
            );


        if (
            title === "Messages"
            || title === "Customer Job Request"
            || title === "Calendar"
            || title === "Job Scheduling"
        ) {

            return;
        }


        button.addEventListener(
            "click",
            function (event) {

                event.preventDefault();


                const feature =
                    button.dataset.feature
                    || "This feature";


                window.alert(
                    feature
                    + " will be added later."
                );
            }
        );
    });


    // =====================================================
    // SUPPLIER SEARCH
    // =====================================================

    const supplierFormButton =
        document.getElementById(
            "find-suppliers-button"
        );


    if (supplierFormButton) {

        const supplierForm =
            supplierFormButton.closest(
                "form"
            );


        if (supplierForm) {

            supplierForm.addEventListener(
                "submit",
                function () {

                    supplierFormButton.disabled =
                        true;


                    supplierFormButton.innerHTML =
                        '<i class="fa-solid fa-spinner fa-spin"></i>'
                        + " Searching...";
                }
            );
        }
    }

});