document.addEventListener("DOMContentLoaded", function() {
    const userInput = document.getElementById("user-input");
    const submitButton = document.getElementById("submit-button");
    const chatContainer = document.getElementById("chat-container");
    const citiButton = document.getElementById("bank-citi");
    const chatSection = document.getElementById("chat-section");
    const devMessage = document.getElementById("development-message");
    const downloadDataSection = document.getElementById("download-data-section");
    const compareReportsSection = document.getElementById("compare-reports-section");
    const downloadButton = document.getElementById("download-button");
    const downloadDataButton = document.getElementById("download-data-button");
    const compareButton = document.getElementById("compare-button");
    const reportModal = new bootstrap.Modal(document.getElementById('reportModal'));
    const reportModalBody = document.getElementById("report-modal-body");
    const downloadReportPdfButton = document.getElementById("download-report-pdf");
    const compareCompanySelect = document.getElementById("compare-company-select");
    const compareFromQuarter = document.getElementById("compare-from-quarter");
    const compareToQuarterContainer = document.getElementById("compare-to-quarter-container");
    const compareToQuarter = document.getElementById("compare-to-quarter");
    const fromQuarterDownload = document.getElementById("from-quarter");
    const toQuarterDownload = document.getElementById("to-quarter");


    const navItems = document.querySelectorAll(".sidebar-item");

    function showChat() {
        chatSection.style.display = "block";
        devMessage.style.display = "none";
        downloadDataSection.style.display = "none";
        compareReportsSection.style.display = "none";
    }

    function showDevMessage() {
        chatSection.style.display = "none";
        devMessage.style.display = "block";
        downloadDataSection.style.display = "none";
        compareReportsSection.style.display = "none";
    }

    function showDownloadData() {
        chatSection.style.display = "none";
        devMessage.style.display = "none";
        downloadDataSection.style.display = "block";
        compareReportsSection.style.display = "none";
    }

    function showCompareReports() {
        chatSection.style.display = "none";
        devMessage.style.display = "none";
        downloadDataSection.style.display = "none";
        compareReportsSection.style.display = "block";
    }

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            if (item.id === "nav-chat") {
                showChat();
            } else if (item.id === "nav-download-data") {
                showDownloadData();
            } else if (item.id === "nav-compare") {
                showCompareReports();
            } else {
                showDevMessage();
            }
        });
    });

    document.querySelectorAll("input[name='compare-mode']").forEach(radio => {
        radio.addEventListener("change", function() {
            if (this.value === "single-company") {
                compareCompanySelect.removeAttribute("multiple");
                compareToQuarterContainer.style.display = "block";
            } else {
                compareCompanySelect.setAttribute("multiple", "multiple");
                compareToQuarterContainer.style.display = "block";
            }
        });
    });


    function addMessageToChat(message, sender) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add(sender === "user" ? "user-message" : "bot-message");
        
        if (typeof message === 'object' && message.type === 'html') {
            const reportContainer = document.createElement('div');
            reportContainer.style.height = '600px';
            reportContainer.style.overflow = 'auto';
            reportContainer.style.border = '1px solid #ddd';
            reportContainer.style.borderRadius = '8px';
            
            const shadow = reportContainer.attachShadow({ mode: 'open' });
            shadow.innerHTML = message.data;

            const rawHtmlDiv = document.createElement('div');
            rawHtmlDiv.classList.add('raw-html-for-pdf');
            rawHtmlDiv.style.display = 'none';
            rawHtmlDiv.innerHTML = message.data;

            messageDiv.innerHTML = `<strong>Assistant:</strong><br>`;
            messageDiv.appendChild(reportContainer);
            messageDiv.appendChild(rawHtmlDiv);

        } else if (typeof message === 'object' && message.type === 'text') {
            messageDiv.innerHTML = `<strong>Assistant:</strong> ${message.data}`;
        } 
        else {
            messageDiv.innerHTML = `<strong>You:</strong> ${message}`;
        }

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            addMessageToChat(message, "user");
            userInput.value = "";

            const formData = new FormData();
            formData.append("message", message);

            const response = await fetch("/chat", {
                method: "POST",
                body: formData
            });

            const data = await response.json();
            addMessageToChat(data, "bot");
        }
    }

    async function fetchCitiReport() {
        showChat();
        const response = await fetch("/citi_report");
        const html = await response.text();
        addMessageToChat({ type: 'html', data: html }, "bot");
    }

    async function downloadChatAsPDF() {
        let chatHTML = "";
        chatContainer.childNodes.forEach(node => {
            const rawHtmlDiv = node.querySelector('.raw-html-for-pdf');
            if (rawHtmlDiv) {
                chatHTML += rawHtmlDiv.innerHTML;
            } else {
                chatHTML += node.outerHTML;
            }
        });

        const formData = new FormData();
        formData.append("chat_html", chatHTML);

        const response = await fetch("/download_pdf", {
            method: "POST",
            body: formData
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "chat_history.pdf";
            document.body.appendChild(a);
            a.click();
            a.remove();
        } else {
            alert("Error generating PDF.");
        }
    }

    async function storeDownloadSelection() {
        const fromQuarter = fromQuarterDownload.value;
        const toQuarter = toQuarterDownload.value;
        const dataTypes = Array.from(document.querySelectorAll("input[type=checkbox]:checked")).map(el => el.value);
        const companies = Array.from(document.getElementById("company-select").selectedOptions).map(el => el.value);

        const formData = new FormData();
        formData.append("from_date", fromQuarter);
        formData.append("to_date", toQuarter);
        dataTypes.forEach(dt => formData.append("data_types", dt));
        companies.forEach(c => formData.append("companies", c));

        const response = await fetch("/store_download_selection", {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        console.log(result);
        alert("Your selections have been stored (see console for details). Download functionality is not yet implemented.");
    }

    async function compareReports() {
        const mode = document.querySelector("input[name='compare-mode']:checked").value;
        const companies = Array.from(document.getElementById("compare-company-select").selectedOptions).map(el => el.value);
        const fromQuarter = compareFromQuarter.value;
        const toQuarter = compareToQuarter.value;

        if (mode === 'single-company' && companies.length > 1) {
            alert("Please select only one company for single company comparison.");
            return;
        }

        if (mode === 'multiple-companies') {
            const fromIndex = Array.from(compareFromQuarter.options).findIndex(option => option.value === fromQuarter);
            const toIndex = Array.from(compareToQuarter.options).findIndex(option => option.value === toQuarter);
            if (fromIndex !== toIndex) {
                alert("For multiple companies, please select the same quarter in both dropdowns.");
                return;
            }
        }

        const formData = new FormData();
        formData.append("mode", mode);
        companies.forEach(c => formData.append("companies", c));
        formData.append("from_quarter", fromQuarter);
        formData.append("to_quarter", toQuarter);


        const response = await fetch("/compare_reports", {
            method: "POST",
            body: formData
        });

        const reportHtml = await response.text();
        reportModalBody.innerHTML = reportHtml;
        reportModal.show();
    }

    async function downloadReportAsPDF() {
        const reportHTML = reportModalBody.innerHTML;
        const formData = new FormData();
        formData.append("chat_html", reportHTML);

        const response = await fetch("/download_pdf", {
            method: "POST",
            body: formData
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "comparison_report.pdf";
            document.body.appendChild(a);
            a.click();
            a.remove();
        } else {
            alert("Error generating PDF.");
        }
    }

    function validateQuarterSelection(fromDropdown, toDropdown) {
        if (fromDropdown.selectedIndex < toDropdown.selectedIndex) {
            toDropdown.selectedIndex = fromDropdown.selectedIndex;
        }
    }

    fromQuarterDownload.addEventListener("change", () => validateQuarterSelection(fromQuarterDownload, toQuarterDownload));
    toQuarterDownload.addEventListener("change", () => validateQuarterSelection(fromQuarterDownload, toQuarterDownload));
    compareFromQuarter.addEventListener("change", () => validateQuarterSelection(compareFromQuarter, compareToQuarter));
    compareToQuarter.addEventListener("change", () => validateQuarterSelection(compareFromQuarter, compareToQuarter));


    submitButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
            sendMessage();
        }
    });

    citiButton.addEventListener("click", fetchCitiReport);
    downloadButton.addEventListener("click", downloadChatAsPDF);
    downloadDataButton.addEventListener("click", storeDownloadSelection);
    compareButton.addEventListener("click", compareReports);
    downloadReportPdfButton.addEventListener("click", downloadReportAsPDF);

    // Show chat by default
    showChat();
    // Set initial state for compare reports
    document.querySelector("input[name='compare-mode']:checked").dispatchEvent(new Event('change'));
});