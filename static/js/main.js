/* ==============================================================================
   SISTEMA DE CONTROLE FINANCEIRO FAMILIAR - JAVASCRIPT PRINCIPAL
   ============================================================================== */

document.addEventListener('DOMContentLoaded', function() {
    // Loading Screen
    setTimeout(function() {
        const loadingScreen = document.querySelector('.loading-screen');
        if (loadingScreen) {
            loadingScreen.classList.add('hidden');
        }
    }, 800);

    // Sidebar Toggle
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.toggle('open');
            } else {
                sidebar.classList.toggle('collapsed');
                localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
            }
        });
    }

    // Restaurar estado do sidebar
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (sidebar && sidebarCollapsed && window.innerWidth > 768) {
        sidebar.classList.add('collapsed');
    }

    // Theme Toggle
    const themeToggle = document.querySelector('.theme-toggle');
    const html = document.documentElement;

    // Verificar tema salvo
    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }

    function updateThemeIcon(theme) {
        if (!themeToggle) return;
        const icon = themeToggle.querySelector('i');
        if (icon) {
            if (theme === 'dark') {
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            } else {
                icon.classList.remove('fa-sun');
                icon.classList.add('fa-moon');
            }
        }
    }

    // Fechar sidebar ao clicar fora (mobile)
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        }
    });

    // Auto-hide alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(-20px)';
            setTimeout(function() {
                alert.remove();
            }, 300);
        }, 5000);
    });

    // Confirm delete
    const deleteForms = document.querySelectorAll('form[data-confirm]');
    deleteForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const message = form.getAttribute('data-confirm') || 'Tem certeza que deseja excluir?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Toggle shopping item (AJAX)
    const shoppingCheckboxes = document.querySelectorAll('.shopping-checkbox');
    shoppingCheckboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            const itemId = checkbox.getAttribute('data-id');
            const itemRow = checkbox.closest('.shopping-item');

            fetch('/shopping/toggle/' + itemId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.is_bought) {
                        itemRow.classList.add('bought');
                    } else {
                        itemRow.classList.remove('bought');
                    }
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });

    // Dynamic user forms on register page
    const userCountInput = document.getElementById('user_count');
    const userFormsContainer = document.getElementById('user-forms-container');

    if (userCountInput && userFormsContainer) {
        userCountInput.addEventListener('change', generateUserForms);
        userCountInput.addEventListener('input', generateUserForms);

        // Gerar formularios iniciais
        generateUserForms();
    }

    function generateUserForms() {
        if (!userCountInput || !userFormsContainer) return;

        const count = parseInt(userCountInput.value) || 1;
        const currentForms = userFormsContainer.querySelectorAll('.user-form-card').length;

        // Remover formularios extras
        if (count < currentForms) {
            const forms = userFormsContainer.querySelectorAll('.user-form-card');
            for (let i = count; i < currentForms; i++) {
                forms[i].remove();
            }
        }

        // Adicionar novos formularios
        for (let i = currentForms + 1; i <= count; i++) {
            const formCard = document.createElement('div');
            formCard.className = 'user-form-card animate-slide-up';
            formCard.innerHTML = `
                <div class="user-form-header">
                    <i class="fas fa-user"></i>
                    <span>Usuario ${i} ${i === 1 ? '(Administrador)' : ''}</span>
                </div>
                <div class="form-group">
                    <label class="form-label">Nome Completo</label>
                    <input type="text" name="name_${i}" class="form-control" placeholder="Ex: Joao Silva" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Username</label>
                    <input type="text" name="username_${i}" class="form-control" placeholder="Ex: joao" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Senha</label>
                    <input type="password" name="password_${i}" class="form-control" placeholder="Minimo 6 caracteres" minlength="6" required>
                </div>
            `;
            userFormsContainer.appendChild(formCard);
        }
    }

    // Expense form - toggle recurring fields
    const isRecurringCheckbox = document.getElementById('is_recurring');
    const recurringFields = document.getElementById('recurring-fields');

    if (isRecurringCheckbox && recurringFields) {
        isRecurringCheckbox.addEventListener('change', function() {
            recurringFields.style.display = this.checked ? 'block' : 'none';
        });
        recurringFields.style.display = isRecurringCheckbox.checked ? 'block' : 'none';
    }

    // Expense form - toggle installment fields
    const isInstallmentCheckbox = document.getElementById('is_installment');
    const installmentFields = document.getElementById('installment-fields');

    if (isInstallmentCheckbox && installmentFields) {
        isInstallmentCheckbox.addEventListener('change', function() {
            installmentFields.style.display = this.checked ? 'block' : 'none';
        });
        installmentFields.style.display = isInstallmentCheckbox.checked ? 'block' : 'none';
    }

    // Initialize Charts
    initCharts();

    // Number formatting
    const currencyElements = document.querySelectorAll('.currency');
    currencyElements.forEach(function(el) {
        const value = parseFloat(el.textContent);
        if (!isNaN(value)) {
            el.textContent = formatCurrency(value);
        }
    });

    // Responsive tables
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(function(table) {
        const container = table.closest('.table-container');
        if (container && window.innerWidth <= 768) {
            container.style.overflowX = 'auto';
        }
    });
});

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

// Initialize Charts
function initCharts() {
    // Category Pie Chart
    const categoryChartEl = document.getElementById('categoryChart');
    if (categoryChartEl && typeof Chart !== 'undefined') {
        const labels = JSON.parse(categoryChartEl.getAttribute('data-labels') || '[]');
        const data = JSON.parse(categoryChartEl.getAttribute('data-values') || '[]');
        const colors = JSON.parse(categoryChartEl.getAttribute('data-colors') || '[]');

        if (labels.length > 0 && data.length > 0) {
            new Chart(categoryChartEl, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: colors.length > 0 ? colors : [
                            '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#3b82f6',
                            '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#64748b'
                        ],
                        borderWidth: 0,
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }
                        }
                    },
                    cutout: '65%'
                }
            });
        }
    }

    // Monthly Bar Chart
    const monthlyChartEl = document.getElementById('monthlyChart');
    if (monthlyChartEl && typeof Chart !== 'undefined') {
        const labels = JSON.parse(monthlyChartEl.getAttribute('data-labels') || '[]');
        const data = JSON.parse(monthlyChartEl.getAttribute('data-values') || '[]');

        if (labels.length > 0 && data.length > 0) {
            new Chart(monthlyChartEl, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Total Gasto',
                        data: data,
                        backgroundColor: 'rgba(99, 102, 241, 0.8)',
                        borderColor: '#6366f1',
                        borderWidth: 2,
                        borderRadius: 8,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0,0,0,0.05)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        }
    }

    // Annual Chart (Reports)
    const annualChartEl = document.getElementById('annualChart');
    if (annualChartEl && typeof Chart !== 'undefined') {
        const labels = JSON.parse(annualChartEl.getAttribute('data-labels') || '[]');
        const data = JSON.parse(annualChartEl.getAttribute('data-values') || '[]');

        if (labels.length > 0 && data.length > 0) {
            new Chart(annualChartEl, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Gastos Mensais',
                        data: data,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#6366f1',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0,0,0,0.05)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        }
    }

    // Person Comparison Chart
    const personChartEl = document.getElementById('personChart');
    if (personChartEl && typeof Chart !== 'undefined') {
        const labels = JSON.parse(personChartEl.getAttribute('data-labels') || '[]');
        const sharedData = JSON.parse(personChartEl.getAttribute('data-shared') || '[]');
        const individualData = JSON.parse(personChartEl.getAttribute('data-individual') || '[]');

        if (labels.length > 0) {
            new Chart(personChartEl, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Compartilhado',
                            data: sharedData,
                            backgroundColor: 'rgba(99, 102, 241, 0.8)',
                            borderRadius: 6
                        },
                        {
                            label: 'Individual',
                            data: individualData,
                            backgroundColor: 'rgba(16, 185, 129, 0.8)',
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0,0,0,0.05)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        }
    }
}

// Export functions
function exportToPDF() {
    window.print();
}

function exportToExcel() {
    alert('Funcionalidade de exportacao para Excel sera implementada em breve.');
}
