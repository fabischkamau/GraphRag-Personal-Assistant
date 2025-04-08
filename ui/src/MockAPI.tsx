"use client";

// This is a mock implementation for testing purposes
// Replace with actual API implementation in production

import { useState } from "react";

// Mock data for testing
const mockResponse = {
  output:
    "Got it! You're looking for the best LED strip lights. I'll search for options across multiple retailers to find high-quality, affordable, and versatile LED strip lights that suit various needs (e.g., home decor, gaming setups, or accent lighting). I'll focus on features like brightness, color options, length, ease of installation, and smart connectivity.\n\nHere are my top recommendations:\n\n---\n\n### 1. [Govee RGBIC LED Strip Lights](https://www.amazon.com/dp/B08C5J1N5M)  \n- **Price**: $29.99  \n- **Retailer**: Amazon  \n- **Key Features**:  \n  - 16.4 ft length with RGBIC technology for multi-color display.  \n  - App control via Bluetooth and voice control with Alexa/Google Assistant.  \n  - Music sync feature for dynamic lighting effects.  \n  - Easy installation with adhesive backing.  \n- **Why I Recommend It**: Govee is a trusted brand for smart lighting, and this model offers vibrant colors, app control, and music sync at an affordable price.\n\n---\n\n### 2. [Philips Hue Lightstrip Plus](https://www.bestbuy.com/site/philips-hue-lightstrip-plus-base-v4/6418587.p)  \n- **Price**: $79.99  \n- **Retailer**: Best Buy  \n- **Key Features**:  \n  - 6.6 ft length, expandable up to 33 ft.  \n  - Works with Philips Hue Bridge for smart home integration.  \n  - Compatible with Alexa, Google Assistant, and Apple HomeKit.  \n  - High-quality lighting with adjustable brightness and color temperature.  \n- **Why I Recommend It**: Ideal for smart home enthusiasts who want seamless integration with other Philips Hue products.\n\n---\n\n### 3. [DAYBETTER LED Strip Lights](https://www.walmart.com/ip/DAYBETTER-32-8ft-RGB-LED-Strip-Lights-with-Remote/474231123)  \n- **Price**: $19.99  \n- **Retailer**: Walmart  \n- **Key Features**:  \n  - 32.8 ft length with RGB color options.  \n  - Comes with a remote control for easy operation.  \n  - Strong adhesive backing for secure installation.  \n  - Cuttable and linkable for customization.  \n- **Why I Recommend It**: Budget-friendly option with a longer length, perfect for larger spaces or DIY projects.\n\n---\n\n### 4. [Kasa Smart LED Strip Lights](https://www.target.com/p/kasa-smart-led-light-strip/-/A-79850132)  \n- **Price**: $49.99  \n- **Retailer**: Target  \n- **Key Features**:  \n  - 16.4 ft length with adjustable RGB colors.  \n  - Wi-Fi-enabled for app control and voice commands via Alexa/Google Assistant.  \n  - Dimmable and customizable lighting effects.  \n  - Energy-efficient design.  \n- **Why I Recommend It**: Great mid-range option with smart features and reliable performance.\n\n---\n\n### 5. [HitLights Waterproof LED Strip Lights](https://www.homedepot.com/p/HitLights-Waterproof-LED-Light-Strip-Kit-16-4-ft-RGB-Color-Changing-with-Remote-Control-LC7066016RGB/313554187)  \n- **Price**: $39.99  \n- **Retailer**: Home Depot  \n- **Key Features**:  \n  - 16.4 ft length with waterproof design for indoor/outdoor use.  \n  - Includes remote control for easy operation.  \n  - RGB color-changing options.  \n  - Durable and flexible construction.  \n- **Why I Recommend It**: Perfect for outdoor use or areas prone to moisture, with a solid build and vibrant lighting.\n\n---\n\n### Suggested Follow-Up Actions:\n1. Compare the features and prices to decide which option fits your needs best (e.g., smart home integration, length, or budget).  \n2. Consider where you'll install the lights (indoor vs. outdoor) and whether you need waterproofing.  \n3. Let me know if you'd like help finding additional options or accessories like connectors or power supplies!  \n\nLet me know if you need further assistance!",
};

export function useMockAPI() {
  const [isWaiting, setIsWaiting] = useState(true);
  const [responseData, setResponseData] = useState<any>(null);

  // Mock API endpoints
  const mockSendData = async (input: string, sessionId: string) => {
    console.log("Sending data:", { input, sessionId });
    // Simulate API call delay
    return new Promise<void>((resolve) => {
      setTimeout(() => {
        setIsWaiting(true);
        resolve();
      }, 500);
    });
  };

  const mockGetResponse = async () => {
    if (isWaiting) {
      // Simulate waiting state for a few seconds
      setTimeout(() => {
        setIsWaiting(false);
        setResponseData({
          status: "completed",
          analysis_result: {
            analysis: [
              {
                name: "Shopping Assistant",
                content: mockResponse.output,
              },
            ],
          },
        });
      }, 3000);

      return { status: "waiting" };
    }

    return responseData;
  };

  return {
    sendData: mockSendData,
    getResponse: mockGetResponse,
    resetResponse: () => {
      setIsWaiting(true);
      setResponseData(null);
    },
  };
}
