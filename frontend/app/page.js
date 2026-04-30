"use client";

import { useState, useEffect } from "react";
import Image from "next/image";

/* SVG Icons to match design without adding heavy dependencies */
const LocationIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
    <circle cx="12" cy="10" r="3"></circle>
  </svg>
);

const DiningIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"></path>
    <path d="M7 2v20"></path>
    <path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"></path>
  </svg>
);

const ChevronIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{color: '#828282', position: 'absolute', right: 16}}>
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

const MoneyIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="6" width="20" height="12" rx="2"></rect>
    <circle cx="12" cy="12" r="2"></circle>
    <path d="M6 12h.01M18 12h.01"></path>
  </svg>
);

const SmartphoneIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect>
    <line x1="12" y1="18" x2="12.01" y2="18"></line>
  </svg>
);

const AutocompleteInput = ({ value, onChange, options, placeholder, icon }) => {
  const [showDropdown, setShowDropdown] = useState(false);
  
  const filteredOptions = options.filter(opt => 
    opt.toLowerCase().includes(value.toLowerCase())
  );

  return (
    <div className="input-wrapper" style={{ position: "relative", width: "100%" }}>
      {icon}
      <input 
        type="text" 
        placeholder={placeholder} 
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setShowDropdown(true);
        }}
        onFocus={() => setShowDropdown(true)}
        onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
        style={{ width: "100%", outline: "none", border: "none", background: "transparent", fontSize: "16px", color: "#1c1c1c", padding: "8px 0" }}
      />
      {showDropdown && filteredOptions.length > 0 && (
        <ul style={{
          position: "absolute",
          top: "calc(100% + 8px)",
          left: 0,
          right: 0,
          backgroundColor: "#fff",
          border: "1px solid #e8e8e8",
          borderRadius: "12px",
          maxHeight: "250px",
          overflowY: "auto",
          zIndex: 50,
          listStyle: "none",
          padding: "8px 0",
          margin: 0,
          boxShadow: "0 8px 24px rgba(0,0,0,0.12)"
        }}>
          {filteredOptions.map((opt, idx) => (
            <li 
              key={idx} 
              style={{ padding: "12px 16px", cursor: "pointer", color: "#333", fontSize: "15px", transition: "background 0.2s" }}
              onMouseDown={() => {
                onChange(opt);
                setShowDropdown(false);
              }}
              onMouseEnter={(e) => e.target.style.backgroundColor = "#f8f8f8"}
              onMouseLeave={(e) => e.target.style.backgroundColor = "transparent"}
            >
              {opt}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default function Home() {
  const [location, setLocation] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [minRating, setMinRating] = useState("4.0+");
  const [budget, setBudget] = useState("");
  const [optionalPrefs, setOptionalPrefs] = useState("");
  const [isVegOnly, setIsVegOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [metadata, setMetadata] = useState({ locations: [], cuisines: [] });

  useEffect(() => {
    const getApiUrl = (path) => {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL;
      if (!base || base === "undefined" || base === "") return path;
      return `${base.replace(/\/$/, "")}${path}`;
    };

    console.log("Fetching metadata from:", getApiUrl("/api/metadata"));
    fetch(getApiUrl("/api/metadata"))
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (data.locations) {
          setMetadata({
            locations: data.locations.sort((a,b) => a.localeCompare(b)),
            cuisines: data.cuisines.sort((a,b) => a.localeCompare(b))
          });
        }
      })
      .catch(console.error);
  }, []);

  const budgetOptions = [
    "Up to 500",
    "500 - 1000",
    "1000 - 1500",
    "1500 - 2000",
    "2000+"
  ];

  const prefOptions = [
    "Quiet Romantic",
    "Rooftop",
    "Vegan Friendly",
    "Family Friendly",
    "Wine",
    "Live Music",
    "Outdoor Seating",
    "Pet Friendly",
    "Great View",
    "Fine Dining"
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const getApiUrl = (path) => {
        const base = process.env.NEXT_PUBLIC_BACKEND_URL;
        if (!base || base === "undefined" || base === "") return path;
        return `${base.replace(/\/$/, "")}${path}`;
      };

      const res = await fetch(getApiUrl("/api/recommend"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          location: location || "Gwalior",
          cuisine: cuisine || "All",
          budget: budget || "medium",
          minimum_rating: minRating.replace("+", ""),
          optional_preferences: optionalPrefs + (isVegOnly ? (optionalPrefs ? ", Pure Veg" : "Pure Veg") : ""),
        }),
      });
      if(res.ok) {
        const data = await res.json();
        setResults(data.recommendations || []);
      } else {
        // Fallback to static dummy data if backend is not wired up yet
        setTimeout(() => {
          setResults([
            {
              id: 1,
              restaurant_name: "The Grand Rooftop",
              cuisine: "North Indian, Italian, Continental",
              location: "City Centre, Gwalior",
              cost_for_two: 1500,
              rating: 4.2,
              image: "/restaurant_1.png",
              mustTry: false
            },
            {
              id: 2,
              restaurant_name: "Cucina Authentica",
              cuisine: "Italian, Pasta, Pizzas",
              location: "Gwalior Fort Road",
              cost_for_two: 1200,
              rating: 4.8,
              image: "/restaurant_2.png",
              mustTry: true
            },
            {
              id: 3,
              restaurant_name: "Zen Garden",
              cuisine: "Japanese, Sushi, Asian Fusion",
              location: "Deen Dayal Nagar",
              cost_for_two: 2200,
              rating: 4.1,
              image: "/restaurant_3.png",
              mustTry: false
            }
          ]);
          setLoading(false);
        }, 1500);
        return;
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const defaultResults = [
    {
      id: 1,
      restaurant_name: "The Grand Rooftop",
      cuisine: "North Indian, Italian, Continental",
      location: "City Centre, Gwalior",
      cost_for_two: 1500,
      rating: 4.2,
      image: "/restaurant_1.png",
      mustTry: false
    },
    {
      id: 2,
      restaurant_name: "Cucina Authentica",
      cuisine: "Italian, Pasta, Pizzas",
      location: "Gwalior Fort Road",
      cost_for_two: 1200,
      rating: 4.8,
      image: "/restaurant_2.png",
      mustTry: true
    },
    {
      id: 3,
      restaurant_name: "Zen Garden",
      cuisine: "Japanese, Sushi, Asian Fusion",
      location: "Deen Dayal Nagar",
      cost_for_two: 2200,
      rating: 4.1,
      image: "/restaurant_3.png",
      mustTry: false
    }
  ];

  const displayResults = results || defaultResults;

  return (
    <>
      <section className="hero">
        <header className="header">
          <div className="header-logo">zomato</div>
          <nav className="header-nav">
            <a href="#" style={{display: 'flex', alignItems: 'center', gap: '8px'}}><SmartphoneIcon/> Get the App</a>
            <a href="#">Investor Relations</a>
            <a href="#">Add restaurant</a>
            <a href="#">Log in</a>
            <a href="#">Sign up</a>
          </nav>
        </header>

        <div className="hero-content">
          <div className="hero-title-logo">zomato</div>
          <h1 className="hero-subtitle">Discover the perfect dining experience<br/>using AI</h1>

          <form className="search-container" onSubmit={handleSubmit}>
            <div className="search-grid">
              <div className="search-group">
                <label>Your Location</label>
                <AutocompleteInput 
                  value={location} 
                  onChange={setLocation} 
                  options={metadata.locations} 
                  placeholder="e.g. Indra Nagar, City Centre" 
                  icon={<LocationIcon />} 
                />
              </div>
              
              <div className="search-group" style={{ position: "relative" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label>Cuisines</label>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", textTransform: "none", color: "#1c1c1c", fontSize: "13px", fontWeight: 600 }}>
                    <input 
                      type="checkbox" 
                      checked={isVegOnly} 
                      onChange={(e) => setIsVegOnly(e.target.checked)} 
                      style={{ width: "16px", height: "16px", accentColor: "#E23744", cursor: "pointer" }}
                    />
                    Veg Only
                  </label>
                </div>
                <AutocompleteInput 
                  value={cuisine} 
                  onChange={setCuisine} 
                  options={metadata.cuisines} 
                  placeholder="e.g. North Indian, Italian" 
                  icon={<DiningIcon />} 
                />
              </div>

              <div className="search-group">
                <label>Minimum Rating</label>
                <div className="input-wrapper">
                  <select value={minRating} onChange={e => setMinRating(e.target.value)} style={{appearance: 'none', WebkitAppearance: 'none', cursor: 'pointer'}}>
                    <option value="3.0+">3.0+</option>
                    <option value="3.5+">3.5+</option>
                    <option value="4.0+">4.0+</option>
                    <option value="4.5+">4.5+</option>
                  </select>
                  <ChevronIcon />
                </div>
              </div>

              <div className="search-group">
                <label>Budget</label>
                <AutocompleteInput 
                  value={budget} 
                  onChange={setBudget} 
                  options={budgetOptions} 
                  placeholder="e.g. 500-1000" 
                  icon={<MoneyIcon />} 
                />
              </div>

              <div className="search-group full">
                <label>Additional Preferences</label>
                <AutocompleteInput 
                  value={optionalPrefs} 
                  onChange={setOptionalPrefs} 
                  options={prefOptions} 
                  placeholder="e.g. Quiet romantic, Rooftop, Vegan friendly" 
                  icon={null} 
                />
              </div>
            </div>

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? "Generating..." : "Generate Recommendations"}
            </button>
          </form>
        </div>
      </section>

      <main className="recommendations-section">
        <div className="section-header">
          <h2>Recommended for You</h2>
          <a href="#" className="view-all">View all</a>
        </div>

        <div className="grid">
          {displayResults.length > 0 ? (
            displayResults.map((rec, idx) => (
              <div key={idx} className="restaurant-card">
                <div className="card-image-wrapper">
                  <Image 
                    src={rec.image || `/restaurant_${(idx % 3) + 1}.png`} 
                    alt={rec.restaurant_name}
                    fill
                    style={{objectFit: 'cover'}}
                  />
                  <div className="card-badges">
                    <div>
                      {rec.mustTry && <span className="tag-must-try">Must Try</span>}
                    </div>
                    <span className="tag-rating">{rec.rating} ☆</span>
                  </div>
                </div>
                <div className="card-content">
                  <div className="card-title">{rec.restaurant_name}</div>
                  <div className="card-cuisines">{rec.cuisine}</div>
                  <div className="card-footer">
                    <span>{rec.location}</span>
                    <span>{rec.cost_for_two ? `₹${rec.cost_for_two.toLocaleString("en-IN")} for two` : "Cost for 2 as per data"}</span>
                  </div>
                  <div className="card-reason" style={{ fontSize: "13px", color: "#4f4f4f", marginTop: "16px", padding: "12px", background: "#f8f8f8", borderRadius: "8px", borderLeft: "3px solid #E23744", lineHeight: "1.4" }}>
                    <strong style={{ color: "#1c1c1c", display: "block", marginBottom: "4px" }}>Why we chose this:</strong> 
                    {rec.reason || "Recommended based on your specific location and dining preferences."}
                  </div>
                </div>
              </div>
            ))
          ) : (
             <div className="empty-state">
                No recommendations found for your search criteria.
             </div>
          )}
        </div>
      </main>

      <footer className="footer">
        <div className="footer-top">
          <div className="footer-logo">zomato</div>
          <div className="footer-selectors">
            <div className="selector">
              <img src="https://upload.wikimedia.org/wikipedia/en/4/41/Flag_of_India.svg" width="16" alt="India flag" />
              India
              <ChevronIcon style={{position:'static'}}/>
            </div>
            <div className="selector">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
              English
              <ChevronIcon style={{position:'static'}}/>
            </div>
          </div>
        </div>

        <div className="footer-links">
          <div className="footer-col">
            <h4>About Zomato</h4>
            <ul>
              <li><a href="#">Who We Are</a></li>
              <li><a href="#">Blog</a></li>
              <li><a href="#">Work With Us</a></li>
              <li><a href="#">Investor Relations</a></li>
              <li><a href="#">Report Fraud</a></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Zomaverse</h4>
            <ul>
              <li><a href="#">Zomato</a></li>
              <li><a href="#">Blinkit</a></li>
              <li><a href="#">Feeding India</a></li>
              <li><a href="#">Hyperpure</a></li>
              <li><a href="#">Zomato Live</a></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>For Restaurants</h4>
            <ul>
              <li><a href="#">Partner With Us</a></li>
              <li><a href="#">Apps For You</a></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Learn More</h4>
            <ul>
              <li><a href="#">Privacy</a></li>
              <li><a href="#">Security</a></li>
              <li><a href="#">Terms</a></li>
              <li><a href="#">Sitemap</a></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Social Links</h4>
            <div className="social-links">
              <div className="social-circle">in</div>
              <div className="social-circle">tw</div>
              <div className="social-circle">ig</div>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          By continuing past this page, you agree to our Terms of Service, Cookie Policy, Privacy Policy and Content Policies. All trademarks are properties of their respective owners. 2008–2026 © Zomato™ Ltd. All rights reserved.
        </div>
      </footer>
    </>
  );
}
