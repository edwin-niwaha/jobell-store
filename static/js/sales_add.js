$(document).ready(function () {
    // Initialize Select2 for the product select dropdown
    $('#searchbox_products').select2({
        placeholder: 'Search for a product...',
        allowClear: true,
        width: '100%'
    });

    const $productSelect = $('#searchbox_products');
    const $productTableBody = $('#table_products tbody');
    const $subTotalInput = $('#sub_total');
    const $taxPercentageInput = $('#tax_percentage');
    const $taxAmountInput = $('#tax_amount');
    const $grandTotalInput = $('#grand_total');
    const $amountPayedInput = $('#amount_payed');
    const $amountChangeInput = $('#amount_change');
    const $form = $('.saleForm');

    let productIndex = 0;
    let selectedProducts = [];

    // Handle product selection
    function handleProductSelection() {
        const $selectedOption = $productSelect.find('option:selected');
        const productId = $selectedOption.val();
        const productName = $selectedOption.data('name');
        const productVolume = $selectedOption.data('volume');
        const productPrice = parseFloat($selectedOption.data('price'));

        // Add product row to the table if it hasn't been added already
        if (productId && !selectedProducts.includes(productId)) {
            selectedProducts.push(productId);
            addProductRow(productId, productName, productVolume, productPrice);
            updateTotals();
        }
    }

    // Add new product row to the table
    function addProductRow(productId, productName, productVolume, productPrice) {
        const newRow = `
      <tr>
        <td>${++productIndex}</td>
        <td>${productName}</td>
        <td>${productVolume}</td>
        <td>${productPrice.toFixed(2)}</td>
        <td><input type="number" class="form-control quantity-input" value="1" min="1" data-price="${productPrice}" data-product-id="${productId}"></td>
        <td class="product-total">${productPrice.toFixed(2)}</td>
        <td class="text-center"><button type="button" class="btn btn-danger btn-sm delete-product" data-product-id="${productId}"><i class="fas fa-trash-alt"></i></button></td>
      </tr>
    `;
        $productTableBody.append(newRow);
    }

    // Update totals when quantity or tax percentage changes
    function updateTotals() {
        let subtotal = 0;
        $('.product-total').each(function () {
            subtotal += parseFloat($(this).text());
        });
        $subTotalInput.val(subtotal.toFixed(2));

        const taxPercentage = parseFloat($taxPercentageInput.val()) || 0;
        const taxAmount = subtotal * (taxPercentage / 100);
        $taxAmountInput.val(taxAmount.toFixed(2));

        const grandTotal = subtotal + taxAmount;
        $grandTotalInput.val(grandTotal.toFixed(2));

        const amountPayed = parseFloat($amountPayedInput.val()) || 0;
        const amountChange = amountPayed - grandTotal;
        $amountChangeInput.val(amountChange.toFixed(2));
    }

    // Update individual product total when quantity changes
    function updateProductTotal($input) {
        const price = parseFloat($input.data('price'));
        const quantity = Math.max(parseInt($input.val()), 1); // Prevent invalid quantities
        const productTotal = price * quantity;
        $input.closest('tr').find('.product-total').text(productTotal.toFixed(2));
    }

    // Remove product when delete button is clicked
    function removeProduct(e) {
        const $button = $(e.target).closest('.delete-product');
        const productId = $button.data('product-id');
        selectedProducts = selectedProducts.filter(id => id !== productId);
        $button.closest('tr').remove();
        updateTotals();
    }

    // Add hidden product data to the form on submit
    function addProductDataToForm(event) {
        const grandTotal = parseFloat($grandTotalInput.val());
        const amountPayed = parseFloat($amountPayedInput.val()) || 0;

        // Prevent form submission if amount paid is less than grand total
        if (amountPayed < grandTotal) {
            event.preventDefault();
            alert('The paid amount must be equal to or greater than the total amount.');
            return false;
        }

        // Remove existing hidden product inputs
        $('input[name="products"]').remove();

        // Add new hidden inputs with product data
        selectedProducts.forEach(productId => {
            const $row = $productTableBody.find('tr').filter(function () {
                return $(this).find('.delete-product').data('product-id') === productId;
            });
            const quantity = parseInt($row.find('.quantity-input').val());
            const price = parseFloat($row.find('.product-total').text()) / quantity;
            const totalProduct = parseFloat($row.find('.product-total').text());

            const input = $('<input>', {
                type: 'hidden',
                name: 'products',
                value: JSON.stringify({
                    id: productId,
                    price: price,
                    quantity: quantity,
                    total_product: totalProduct
                })
            });
            $form.append(input);
        });
    }

    // Event Listeners
    $productSelect.on('change', handleProductSelection);
    $productTableBody.on('input', '.quantity-input', function () {
        updateProductTotal($(this));
        updateTotals();
    });
    $productTableBody.on('click', '.delete-product', removeProduct);
    $taxPercentageInput.on('input', updateTotals);
    $amountPayedInput.on('keyup', updateTotals);
    $form.on('submit', addProductDataToForm);
});
