function chatbotReply(msg){
  msg = msg.toLowerCase();

  function chatbotReply(msg){
  msg = msg.toLowerCase();

  if(msg.includes("hello") || msg.includes("hi") || msg.includes("hey")){
    return "Hi, Welcome to Construct Hub! I can help you with products, cart, orders, and payments.";
  }

  if(msg.includes("product") || msg.includes("items")){
    return "We offer cement, steel, tools, safety equipment and more. Visit the products page to explore.";
  }

  if(msg.includes("cement")){
    return "We have high-quality cement products available at affordable prices.";
  }

  if(msg.includes("steel")){
    return "We provide strong and durable steel rods for construction.";
  }

  if(msg.includes("cart")){
    return "You can add items to cart from the products page and view them in the cart section.";
  }

  if(msg.includes("add to cart")){
    return "Click on the 'Add to Cart' button below any product.";
  }

  if(msg.includes("payment") || msg.includes("pay")){
    return "We support Card, UPI, and Cash on Delivery payments.";
  }

  if(msg.includes("checkout")){
    return "Go to the checkout page, enter your address, and confirm your order.";
  }

  if(msg.includes("login")){
    return "You can login from the accounts page using your registered email and password.";
  }

  if(msg.includes("signup") || msg.includes("register")){
    return "Create an account using the signup form on the accounts page.";
  }

  if(msg.includes("order status") || msg.includes("track")){
    return "Order tracking is currently basic. Please check your account section.";
  }

  if(msg.includes("order")){
    return "After checkout and payment, your order will be placed successfully.";
  }

  if(msg.includes("help") || msg.includes("support")){
    return "I'm here to help! Ask me about products, cart, payments or login.";
  }

  if(msg.includes("contact")){
    return "You can contact us at support@constructhub.com";
  }

  return "Sorry I did not understand that. Try asking about products, cart, or payment.";
}
}

function sendMessage(){
  let input = document.getElementById("chatInput");
  let chat = document.getElementById("chatBox");

  let userMsg = input.value;
  chat.innerHTML += `<p><b>You:</b> ${userMsg}</p>`;
  chat.innerHTML += `<p><b>Bot:</b> ${chatbotReply(userMsg)}</p>`;

  input.value = "";
}